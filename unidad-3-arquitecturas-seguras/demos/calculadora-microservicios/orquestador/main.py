import logging
import os
import time
from datetime import datetime, timezone
from typing import List, Optional
from opentelemetry import trace
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import mysql.connector
import requests
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('calculadora-orquestador')
trace.set_tracer_provider(TracerProvider(resource=Resource.create({'service.name': 'orquestador'})))
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ZipkinExporter(endpoint=os.environ.get('ZIPKIN_ENDPOINT', 'http://zipkin:9411/api/v2/spans'))))
RequestsInstrumentor().instrument()
URL_SUMA = os.environ.get('URL_SUMA', 'http://servicio-suma:8000')
URL_RESTA = os.environ.get('URL_RESTA', 'http://servicio-resta:8000')
URL_MULTIPLICACION = os.environ.get('URL_MULTIPLICACION', 'http://servicio-multiplicacion:8000')
URL_DIVISION = os.environ.get('URL_DIVISION', 'http://servicio-division:8000')
URLS_POR_NOMBRE = {'suma': URL_SUMA, 'resta': URL_RESTA, 'multiplicacion': URL_MULTIPLICACION, 'division': URL_DIVISION}
TIMEOUT_SEG = 5
DB_CONFIG = {'host': os.environ.get('DB_HOST', 'db'), 'user': os.environ.get('DB_USER', 'app_user'), 'password': os.environ.get('DB_PASSWORD', 'app_password'), 'database': os.environ.get('DB_NAME', 'calculadora'), 'charset': 'utf8mb4'}

def _conexion_db(reintentos: int=10, espera_seg: float=2.0):
    ultimo_error = None
    for _ in range(reintentos):
        try:
            return mysql.connector.connect(**DB_CONFIG)
        except mysql.connector.Error as exc:
            ultimo_error = exc
            time.sleep(espera_seg)
    raise RuntimeError(f'No se pudo conectar a MySQL tras {reintentos} intentos: {ultimo_error}')

def _registrar_operacion(tipo: str, operando_a: float, operando_b: float, resultado: float, expresion: Optional[str]=None) -> None:
    conn = _conexion_db()
    try:
        cur = conn.cursor()
        cur.execute('INSERT INTO operaciones (tipo, operando_a, operando_b, resultado, expresion, creado_en) VALUES (%s, %s, %s, %s, %s, %s)', (tipo, operando_a, operando_b, resultado, expresion, datetime.now(timezone.utc)))
        conn.commit()
    finally:
        conn.close()

def _llamar_servicio(url_base: str, a: float, b: float) -> float:
    try:
        resp = requests.post(f'{url_base}/operar', json={'a': a, 'b': b}, timeout=TIMEOUT_SEG)
    except requests.exceptions.RequestException as exc:
        logger.exception('Error de red llamando a %s', url_base)
        raise HTTPException(status_code=502, detail=f'No se pudo contactar el servicio en {url_base}: {exc}')
    if resp.status_code != 200:
        detalle = resp.json().get('detail', resp.text) if resp.content else resp.text
        raise HTTPException(status_code=resp.status_code, detail=detalle)
    return resp.json()['resultado']

def _resultado(operacion: str, a: float, b: float, resultado: float) -> dict:
    return {'operacion': operacion, 'operandos': [a, b], 'resultado': resultado}
app = FastAPI(title='Calculadora - orquestador de micro-servicios (demo educativa)', description='Unidad 3 - Arquitecturas comunes. Variante 2 de 5: micro-servicios.')
FastAPIInstrumentor.instrument_app(app)

@app.middleware('http')
async def _registrar_peticiones(request: Request, call_next):
    cuerpo_peticion = await request.body()
    logger.info('-> %s %s query=%s body=%s', request.method, request.url.path, dict(request.query_params), cuerpo_peticion.decode(errors='replace') or '-')
    respuesta = await call_next(request)
    cuerpo_respuesta = b''.join([fragmento async for fragmento in respuesta.body_iterator])
    logger.info('<- %s %s status=%s body=%s', request.method, request.url.path, respuesta.status_code, cuerpo_respuesta.decode(errors='replace'))
    encabezados = dict(respuesta.headers)
    encabezados.pop('content-length', None)
    return Response(content=cuerpo_respuesta, status_code=respuesta.status_code, headers=encabezados, media_type=respuesta.media_type)

@app.get('/api/sumar')
def sumar(a: float=Query(...), b: float=Query(...)) -> dict:
    r = _llamar_servicio(URL_SUMA, a, b)
    _registrar_operacion('suma', a, b, r)
    return _resultado('suma', a, b, r)

@app.get('/api/restar')
def restar(a: float=Query(...), b: float=Query(...)) -> dict:
    r = _llamar_servicio(URL_RESTA, a, b)
    _registrar_operacion('resta', a, b, r)
    return _resultado('resta', a, b, r)

@app.get('/api/multiplicar')
def multiplicar(a: float=Query(...), b: float=Query(...)) -> dict:
    r = _llamar_servicio(URL_MULTIPLICACION, a, b)
    _registrar_operacion('multiplicacion', a, b, r)
    return _resultado('multiplicacion', a, b, r)

@app.get('/api/dividir')
def dividir(a: float=Query(...), b: float=Query(...)) -> JSONResponse:
    r = _llamar_servicio(URL_DIVISION, a, b)
    _registrar_operacion('division', a, b, r)
    return JSONResponse(_resultado('division', a, b, r))

class PasoEntrada(BaseModel):
    operacion: str
    operando: float

class ExpresionEntrada(BaseModel):
    valor_inicial: float
    pasos: List[PasoEntrada]

@app.post('/api/expresion')
def evaluar_expresion(datos: ExpresionEntrada) -> dict:
    if not datos.pasos:
        raise HTTPException(status_code=400, detail='Se necesita al menos un paso')
    valor_actual = datos.valor_inicial
    pasos_resueltos = []
    nombres_pasos = []
    for paso in datos.pasos:
        url_servicio = URLS_POR_NOMBRE.get(paso.operacion)
        if url_servicio is None:
            raise HTTPException(status_code=400, detail=f"Operacion desconocida: {paso.operacion!r}. Debe ser una de: {', '.join(URLS_POR_NOMBRE)}")
        operando_a = valor_actual
        valor_actual = _llamar_servicio(url_servicio, operando_a, paso.operando)
        pasos_resueltos.append(_resultado(paso.operacion, operando_a, paso.operando, valor_actual))
        nombres_pasos.append(paso.operacion)
    _registrar_operacion('expresion', datos.valor_inicial, None, valor_actual, expresion=' -> '.join(nombres_pasos))
    return {'valor_inicial': datos.valor_inicial, 'pasos': pasos_resueltos, 'resultado_final': valor_actual}

@app.get('/api/historial')
def historial(limite: int=Query(default=20, le=200)) -> dict:
    conn = _conexion_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT id, tipo, operando_a, operando_b, resultado, expresion, creado_en FROM operaciones ORDER BY id DESC LIMIT %s', (limite,))
        filas = cur.fetchall()
        for fila in filas:
            fila['creado_en'] = fila['creado_en'].isoformat()
        return {'total_devuelto': len(filas), 'operaciones': filas}
    finally:
        conn.close()

@app.get('/api/salud')
def salud() -> dict:
    return {'ok': True, 'servicio': 'calculadora-micro-servicios'}
