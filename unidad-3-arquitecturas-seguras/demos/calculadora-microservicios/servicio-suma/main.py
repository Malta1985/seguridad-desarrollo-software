import logging
import os
from pathlib import Path

from opentelemetry import trace
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("servicio-suma")

trace.set_tracer_provider(TracerProvider(resource=Resource.create({"service.name": "servicio-suma"})))
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ZipkinExporter(endpoint=os.environ.get("ZIPKIN_ENDPOINT", "http://zipkin:9411/api/v2/spans")))
)

app = FastAPI(title="Servicio de suma (demo educativa)")
FastAPIInstrumentor.instrument_app(app)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def _registrar_peticiones(request: Request, call_next):
    """Deja un rastro en consola de cada peticion que llega (con sus
    parametros) y de la respuesta que se envio -- para poder confirmar,
    en vivo, que fue ESTE contenedor especifico el que atendio la
    llamada, sin tener que instrumentar cada endpoint por separado.

    Los archivos estaticos (/static/*) solo se registran de forma breve
    -- volcar el HTML/CSS/JS completo en cada carga de pagina no aporta
    nada y ensucia la consola justo cuando mas se necesita ver el
    trafico de la API."""
    es_estatico = request.url.path == "/" or request.url.path.startswith("/static/")
    cuerpo_peticion = b"" if es_estatico else await request.body()
    if not es_estatico:
        logger.info(
            "-> %s %s query=%s body=%s",
            request.method, request.url.path, dict(request.query_params),
            cuerpo_peticion.decode(errors="replace") or "-",
        )

    respuesta = await call_next(request)
    cuerpo_respuesta = b"".join([fragmento async for fragmento in respuesta.body_iterator])

    if es_estatico:
        logger.info("-- %s %s status=%s (archivo estatico, body omitido)", request.method, request.url.path, respuesta.status_code)
    else:
        logger.info(
            "<- %s %s status=%s body=%s",
            request.method, request.url.path, respuesta.status_code,
            cuerpo_respuesta.decode(errors="replace"),
        )

    encabezados = dict(respuesta.headers)
    encabezados.pop("content-length", None)
    return Response(
        content=cuerpo_respuesta,
        status_code=respuesta.status_code,
        headers=encabezados,
        media_type=respuesta.media_type,
    )


@app.get("/")
def index() -> FileResponse:
    """Mini cliente web para probar este servicio aislado -- ver
    static/app.js. NO es el cliente principal de la calculadora (ese
    vive en el orquestador): este solo sabe hablar con /operar."""
    return FileResponse(STATIC_DIR / "index.html")


class OperandosEntrada(BaseModel):
    a: float
    b: float


@app.post("/operar")
def operar(datos: OperandosEntrada) -> dict:
    return {"resultado": datos.a + datos.b}


@app.get("/salud")
def salud() -> dict:
    """El orquestador podria usar esto para health-checks; esta demo no
    lo hace, pero queda disponible siguiendo la misma convencion de
    /api/salud que usan las otras variantes."""
    return {"ok": True, "servicio": "servicio-suma"}
