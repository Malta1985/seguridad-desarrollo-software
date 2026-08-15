import logging
import os
import time
from pathlib import Path
import bcrypt
import mysql.connector
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('biblioteca-segura')
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'static'
MENSAJE_ERROR_GENERICO = 'Ocurrió un error al procesar la solicitud. Intenta nuevamente.'
USERNAME_ALLOWLIST = r'^[A-Za-z0-9._-]+$'
TITULO_ALLOWLIST = r'^[A-Za-zÁÉÍÓÚÜáéíóúüÑñ0-9 ,.:-]*$'
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
app = FastAPI(title='Portal Biblioteca UM - VERSION SEGURA (demo educativa)', description='Correccion de SQL Injection (OWASP A05:2025) del mismo dominio.')
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

@app.get('/registro')
def pagina_registro() -> FileResponse:
    return FileResponse(STATIC_DIR / 'registro.html')

@app.get('/api/libros')
def listar_libros() -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT titulo, autor, anio, disponible FROM libros ORDER BY titulo')
        filas = cur.fetchall()
        libros = [{'titulo': fila['titulo'], 'autor': fila['autor'], 'anio': fila['anio'], 'disponible': bool(fila['disponible'])} for fila in filas]
        return {'ok': True, 'resultados': libros}
    finally:
        conn.close()

@app.get('/api/buscar')
def buscar_libros(titulo: str=Query(default='', max_length=100, pattern=TITULO_ALLOWLIST)) -> JSONResponse:
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        query = 'SELECT titulo, autor FROM libros WHERE titulo LIKE %s'
        parametro = f'%{titulo}%'
        cur.execute(query, (parametro,))
        filas = cur.fetchall()
        resultados = [{'titulo': fila['titulo'], 'autor': fila['autor']} for fila in filas]
        return JSONResponse({'ok': True, 'resultados': resultados, 'consulta_sql_plantilla': query, 'valor_recibido_como_dato': titulo})
    except mysql.connector.Error:
        logger.exception('Error de base de datos ejecutando busqueda')
        return JSONResponse(status_code=500, content={'ok': False, 'mensaje': MENSAJE_ERROR_GENERICO})
    finally:
        conn.close()

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, pattern=USERNAME_ALLOWLIST)
    password: str = Field(..., min_length=1, max_length=100)

@app.post('/api/login')
def login(datos: LoginRequest) -> JSONResponse:
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        query = 'SELECT id, username, password FROM usuarios WHERE username = %s'
        cur.execute(query, (datos.username,))
        fila = cur.fetchone()
        password_valida = fila is not None and bcrypt.checkpw(datos.password.encode('utf-8'), fila['password'].encode('utf-8'))
        if password_valida:
            return JSONResponse({'ok': True, 'usuario': {'id': fila['id'], 'username': fila['username']}, 'consulta_sql_plantilla': query})
        return JSONResponse({'ok': False, 'mensaje': 'Usuario o contraseña incorrectos', 'consulta_sql_plantilla': query})
    except mysql.connector.Error:
        logger.exception('Error de base de datos ejecutando login')
        return JSONResponse(status_code=500, content={'ok': False, 'mensaje': MENSAJE_ERROR_GENERICO})
    finally:
        conn.close()

class RegistroRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, pattern=USERNAME_ALLOWLIST)
    password: str = Field(..., min_length=1, max_length=100)

@app.post('/api/registro')
def registro(datos: RegistroRequest) -> JSONResponse:
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT id FROM usuarios WHERE username = %s', (datos.username,))
        if cur.fetchone() is not None:
            return JSONResponse(status_code=409, content={'ok': False, 'mensaje': f"El usuario '{datos.username}' ya existe."})
        password_bytes = datos.password.encode('utf-8')
        sal = bcrypt.gensalt(rounds=12)
        hash_final = bcrypt.hashpw(password_bytes, sal).decode('utf-8')
        cur.execute('INSERT INTO usuarios (username, password) VALUES (%s, %s)', (datos.username, hash_final))
        conn.commit()
        return JSONResponse({
            'ok': True,
            'usuario': {'id': cur.lastrowid, 'username': datos.username},
            'consulta_sql_plantilla': 'INSERT INTO usuarios (username, password) VALUES (%s, %s)',
            'paso_a_paso': {
                '1_password_en_texto_plano': datos.password,
                '2_sal_generada_bcrypt_gensalt_rounds12': sal.decode('utf-8'),
                '3_hash_completo_bcrypt_hashpw': hash_final,
                '4_desglose_del_hash_completo': {
                    'algoritmo_y_costo': hash_final[:7],
                    'sal_embebida_22_chars': hash_final[7:29],
                    'hash_resultante_31_chars': hash_final[29:],
                },
                'nota': 'La sal embebida en el paso 4 es EXACTAMENTE la del paso 2 -- aqui se muestra tal como quedo dentro del string de 60 caracteres que se guardo en la columna password.',
            },
        })
    except mysql.connector.Error:
        logger.exception('Error de base de datos ejecutando registro')
        return JSONResponse(status_code=500, content={'ok': False, 'mensaje': MENSAJE_ERROR_GENERICO})
    finally:
        conn.close()
