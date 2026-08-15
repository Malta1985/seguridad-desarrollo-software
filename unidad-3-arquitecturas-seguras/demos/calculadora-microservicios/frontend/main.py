import asyncio
import logging
import os
from pathlib import Path
from opentelemetry import trace
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'static'
ORQUESTADOR_URL = os.environ.get('ORQUESTADOR_URL', 'http://orquestador:8000')
TIMEOUT_SEG = 10
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('frontend')
trace.set_tracer_provider(TracerProvider(resource=Resource.create({'service.name': 'frontend'})))
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ZipkinExporter(endpoint=os.environ.get('ZIPKIN_ENDPOINT', 'http://zipkin:9411/api/v2/spans'))))
RequestsInstrumentor().instrument()
app = FastAPI(title='Calculadora - frontend (demo educativa)')
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

@app.api_route('/api/{ruta:path}', methods=['GET', 'POST'])
async def proxy_api(ruta: str, request: Request):
    cuerpo = await request.body()

    def _reenviar() -> requests.Response:
        return requests.request(method=request.method, url=f'{ORQUESTADOR_URL}/api/{ruta}', params=request.query_params, data=cuerpo, headers={'content-type': request.headers.get('content-type', 'application/json')}, timeout=TIMEOUT_SEG)
    resp = await asyncio.to_thread(_reenviar)
    return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get('content-type', 'application/json'))
