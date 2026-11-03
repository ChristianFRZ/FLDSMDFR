"""Gateway de FLDSMDFR: la única puerta pública (puerto 8000).

Para cada petición: decide el servicio por prefijo (app/routes.py), pide al directorio las
instancias vivas y elige una en round-robin (app/shared/discovery.py), y reenvía en streaming
(app/proxy.py). Marca cada respuesta con `X-Gateway-Instancia`; el servicio pone `X-Instancia`.
"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import proxy, routes
from app.config import get_settings
from app.shared import discovery

_METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.discovery_enabled:
        await discovery.register(settings.service_name, settings.service_port)
    yield
    if settings.discovery_enabled:
        await discovery.deregister()


app = FastAPI(
    title="FLDSMDFR · gateway", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan
)


@app.middleware("http")
async def x_gateway_instancia(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Gateway-Instancia"] = discovery.instance_id()
    return response


@app.get("/api/health")
async def health():
    """Salud del gateway. Dice además si alcanza al directorio."""
    try:
        r = await discovery._consul().get("/v1/status/leader")
        directory = "ok" if r.status_code == 200 else "error"
    except httpx.HTTPError:
        directory = "error"
    return {"status": "ok", "directory": directory}


def _too_large(service: str) -> JSONResponse:
    # Mismos errores que daba el monolito para cada tipo de subida.
    if service == "catalog-streaming":
        return _error(422, "file_too_large", "El archivo supera el tamaño máximo permitido.")
    return _error(413, "image_too_large", "La imagen pesa más de 2 MB.")


@app.api_route("/{path:path}", methods=_METHODS, include_in_schema=False)
async def gateway(path: str, request: Request):
    service = routes.service_for(request.url.path)
    if service is routes.BLOCKED:
        return _error(404, "not_found", "No encontramos lo que buscas.")
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > get_settings().max_body_bytes:
        return _too_large(service)
    try:
        return await proxy.forward(service, request)
    except proxy.Unavailable as exc:
        return _error(
            503,
            "service_unavailable",
            f"El servicio {exc.service} no está disponible. Intenta de nuevo en un momento.",
        )
