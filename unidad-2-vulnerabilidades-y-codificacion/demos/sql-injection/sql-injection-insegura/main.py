import logging
import os
import time
from pathlib import Path
import mysql.connector
from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('biblioteca-insegura')
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'static'
DB_CONFIG = {'host': os.environ.get('DB_HOST', 'db'), 'user': os.environ.get('DB_USER', 'app_user'), 'password': os.environ.get('DB_PASSWORD', 'app_password'), 'database': os.environ.get('DB_NAME', 'biblioteca'), 'charset': 'utf8mb4'}

def get_connection(reintentos: int=10, espera_seg: float=2.0):
    ultimo_error = None
    for _ in range(reintentos):
        try:
            return mysql.connector.connect(**DB_CONFIG)
        except mysql.connector.Error as exc:
            ultimo_error = exc
            time.sleep(espera_seg)
    raise RuntimeError(f'No se pudo conectar a MySQL tras {reintentos} intentos: {ultimo_error}')
app = FastAPI(title='Portal Biblioteca UM - VERSION INSEGURA (demo educativa)', description='Demo de SQL Injection (OWASP A05:2025) - NO usar este patron en produccion.')
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')

@app.get('/')
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / 'index.html')

@app.get('/buscar')
def pagina_buscar() -> FileResponse:
    return FileResponse(STATIC_DIR / 'buscar.html')

@app.get('/dashboard')
def pagina_dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / 'dashboard.html')

@app.get('/api/libros')
def listar_libros() -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT titulo, autor, anio, disponible FROM libros ORDER BY titulo')
        filas = cur.fetchall()
        libros = [{'titulo': r[0], 'autor': r[1], 'anio': r[2], 'disponible': bool(r[3])} for r in filas]
        return {'ok': True, 'resultados': libros}
    finally:
        conn.close()

@app.get('/api/buscar')
def buscar_libros(titulo: str=Query(default='')) -> JSONResponse:
    conn = get_connection()
    try:
        cur = conn.cursor()
        query = f"SELECT titulo, autor FROM libros WHERE titulo LIKE '%{titulo}%'"
        cur.execute(query)
        filas = cur.fetchall()
        resultados = [{'titulo': r[0], 'autor': r[1]} for r in filas]
        return JSONResponse({'ok': True, 'resultados': resultados, 'consulta_sql_ejecutada': query})
    except Exception as exc:
        logger.exception('Error ejecutando busqueda')
        return JSONResponse(status_code=500, content={'ok': False, 'mensaje': f'Error de base de datos: {exc}'})
    finally:
        conn.close()

@app.post('/api/login')
async def login(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={'ok': False, 'mensaje': 'JSON invalido'})
    username = body.get('username', '')
    password = body.get('password', '')
    conn = get_connection()
    try:
        cur = conn.cursor()
        query = f"SELECT id, username FROM usuarios WHERE username = '{username}' AND password = '{password}'"
        cur.execute(query)
        fila = cur.fetchone()
        if fila is not None:
            return JSONResponse({'ok': True, 'usuario': {'id': fila[0], 'username': fila[1]}, 'consulta_sql_ejecutada': query})
        return JSONResponse({'ok': False, 'mensaje': 'Usuario o contraseña incorrectos', 'consulta_sql_ejecutada': query})
    except Exception as exc:
        logger.exception('Error ejecutando login')
        return JSONResponse(status_code=500, content={'ok': False, 'mensaje': f'Error de base de datos: {exc}'})
    finally:
        conn.close()
