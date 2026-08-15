import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from typing import List
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
OPERACIONES = {'suma': lambda a, b: a + b, 'resta': lambda a, b: a - b, 'multiplicacion': lambda a, b: a * b, 'division': lambda a, b: a / b}
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'calculadora.db'
STATIC_DIR = BASE_DIR / 'static'
app = FastAPI(title='Calculadora - arquitectura cliente-servidor (demo educativa)', description='Unidad 3 - Arquitecturas comunes. Variante 1 de 5: un solo servidor.')
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')

@app.get('/')
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / 'index.html')

def _conexion() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db() -> None:
    conn = _conexion()
    try:
        conn.execute('\n            CREATE TABLE IF NOT EXISTS operaciones (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                tipo TEXT NOT NULL,\n                operando_a REAL,\n                operando_b REAL,\n                resultado REAL NOT NULL,\n                expresion TEXT,\n                creado_en TEXT NOT NULL\n            )\n            ')
        conn.commit()
    finally:
        conn.close()

def _registrar_operacion(tipo: str, operando_a: float, operando_b: float, resultado: float, expresion: Optional[str]=None) -> None:
    conn = _conexion()
    try:
        conn.execute('INSERT INTO operaciones (tipo, operando_a, operando_b, resultado, expresion, creado_en) VALUES (?, ?, ?, ?, ?, ?)', (tipo, operando_a, operando_b, resultado, expresion, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    finally:
        conn.close()
_init_db()

def _resultado(operacion: str, a: float, b: float, resultado: float) -> dict:
    return {'operacion': operacion, 'operandos': [a, b], 'resultado': resultado}

@app.get('/api/sumar')
def sumar(a: float=Query(...), b: float=Query(...)) -> dict:
    r = a + b
    _registrar_operacion('suma', a, b, r)
    return _resultado('suma', a, b, r)

@app.get('/api/restar')
def restar(a: float=Query(...), b: float=Query(...)) -> dict:
    r = a - b
    _registrar_operacion('resta', a, b, r)
    return _resultado('resta', a, b, r)

@app.get('/api/multiplicar')
def multiplicar(a: float=Query(...), b: float=Query(...)) -> dict:
    r = a * b
    _registrar_operacion('multiplicacion', a, b, r)
    return _resultado('multiplicacion', a, b, r)

@app.get('/api/dividir')
def dividir(a: float=Query(...), b: float=Query(...)) -> JSONResponse:
    if b == 0:
        raise HTTPException(status_code=400, detail='No se puede dividir entre cero')
    r = a / b
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
        if paso.operacion not in OPERACIONES:
            raise HTTPException(status_code=400, detail=f"Operacion desconocida: {paso.operacion!r}. Debe ser una de: {', '.join(OPERACIONES)}")
        if paso.operacion == 'division' and paso.operando == 0:
            raise HTTPException(status_code=400, detail='No se puede dividir entre cero')
        operando_a = valor_actual
        valor_actual = OPERACIONES[paso.operacion](operando_a, paso.operando)
        pasos_resueltos.append(_resultado(paso.operacion, operando_a, paso.operando, valor_actual))
        nombres_pasos.append(paso.operacion)
    _registrar_operacion('expresion', datos.valor_inicial, None, valor_actual, expresion=' -> '.join(nombres_pasos))
    return {'valor_inicial': datos.valor_inicial, 'pasos': pasos_resueltos, 'resultado_final': valor_actual}

@app.get('/api/historial')
def historial(limite: int=Query(default=20, le=200)) -> dict:
    conn = _conexion()
    try:
        filas = conn.execute('SELECT id, tipo, operando_a, operando_b, resultado, expresion, creado_en FROM operaciones ORDER BY id DESC LIMIT ?', (limite,)).fetchall()
        return {'total_devuelto': len(filas), 'operaciones': [dict(fila) for fila in filas]}
    finally:
        conn.close()

@app.get('/api/salud')
def salud() -> dict:
    return {'ok': True, 'servicio': 'calculadora-cliente-servidor'}
