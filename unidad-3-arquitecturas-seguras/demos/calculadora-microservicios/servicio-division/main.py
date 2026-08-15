import logging
import os
from pathlib import Path
from opentelemetry import trace
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'static'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('servicio-division')
trace.set_tracer_provider(TracerProvider(resource=Resource.create({'service.name': 'servicio-division'})))
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ZipkinExporter(endpoint=os.environ.get('ZIPKIN_ENDPOINT', 'http://zipkin:9411/api/v2/spans'))))
app = FastAPI(title='Servicio de division (demo educativa)')
FastAPIInstrumentor.instrument_app(app)
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')

@app.middleware('http')
async def _registrar_peticiones(request: Request, call_next):
    es_estatico = request.url.path == '/' or request.url.path.startswith('/static/')
    cuerpo_peticion = b'' if es_estatico else await request.body()
    if not es_estatico:
        logger.info('-> %s %s query=%s body=%s', request.method, request.url.path, dict(request.query_params), cuerpo_peticion.decode(errors='replace') or '-')
    respuesta = await call_next(request)
    cuerpo_respuesta = b''.join([fragmento async for fragmento in respuesta.body_iterator])
    if es_estatico:
        logger.info('-- %s %s status=%s (archivo estatico, body omitido)', request.method, request.url.path, respuesta.status_code)
    else:
        logger.info('<- %s %s status=%s body=%s', request.method, request.url.path, respuesta.status_code, cuerpo_respuesta.decode(errors='replace'))
    encabezados = dict(respuesta.headers)
    encabezados.pop('content-length', None)
    return Response(content=cuerpo_respuesta, status_code=respuesta.status_code, headers=encabezados, media_type=respuesta.media_type)

@app.get('/')
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / 'index.html')

class OperandosEntrada(BaseModel):
    a: float
    b: float

@app.post('/operar')
def operar(datos: OperandosEntrada) -> dict:
    if datos.b == 0:
        raise HTTPException(status_code=400, detail='No se puede dividir entre cero')
    return {'resultado': datos.a / datos.b}

@app.get('/salud')
def salud() -> dict:
    return {'ok': True, 'servicio': 'servicio-division'}
