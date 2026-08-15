import os
import time

import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(
    title="Directorio clientes -- demo cliente-servidor/HTTP",
    description="unidad-1-fundamentos-desarrollo-seguro (Universidad de Manizales)",
)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "db"),
    "user": os.environ.get("DB_USER", "app_user"),
    "password": os.environ.get("DB_PASSWORD", "app_pass"),
    "database": os.environ.get("DB_NAME", "directorio_clientes"),
    "charset": "utf8mb4",
}

def get_connection(reintentos: int = 10, espera_seg: float = 2.0)
    ultimo_error = None
    for intento in range(reintentos):
        try:
            return mysql.connector.connect(**DB_CONFIG)
        except mysql.connector.Error as exc:
            ultimo_error = exc
            time.sleep(espera_seg)
    raise RuntimeError(f"Error al conectar a la base de datos {reintentos} intentos: {ultimo_error}")

class Cliente(BaseModel):
    id: int = Field(..., example=1)
    nombre: str = Field(min_length=1, max_length=100)
    correo: str = Field(min_length=3, max_length=150)
    categoria: int = Field(ge=1, le=4)

@app.post("/api/clientes", status_code=201)
def crear_cliente(cliente: Cliente):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO clientes (id, nombre, correo, categoria) VALUES (%s, %s, %s, %s)",
            (cliente.id, cliente.nombre, cliente.correo, cliente.categoria),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Cliente creado exitosamente"}
    except mysql.connector.Error as exc:
        raise HTTPException(status_code=500, detail=f"Error al crear el cliente: {exc}")

@app.get("/api/clientes")
def obtener_cliente():
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, correo, categoria FROM clientes ORDENR BY id")
        cliente = cursor.fetchone()
        filas = cursor.fetchall()
        return {"total": len(filas), "clientes": filas}
    finally:
        conn.close()

@app.put("/api/clientes/{cliente_id}")
def actualizar_cliente(cliente_id: int, cliente: Cliente):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE clientes SET nombre = %s, correo = %s, categoria = %s WHERE id = %s",
            (cliente.nombre, cliente.correo, cliente.categoria, cliente_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return {"message": "Cliente actualizado exitosamente"}
    finally:
        conn.close()    

@app.delete("/api/clientes/{cliente_id}")
def eliminar_cliente(cliente_id: int):  
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return {"message": "Cliente eliminado exitosamente"}
    finally:
        conn.close()