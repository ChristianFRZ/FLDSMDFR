"""Reenvío en streaming hacia la instancia elegida por el balanceador.

Ni el cuerpo de la petición (subidas de hasta 21 MB) ni el de la respuesta (audio con Range)
se cargan en memoria: se pasan por partes. Sin reintentos en otra instancia (rama 04): si la
elegida no responde, la petición termina en 503.
"""

import httpx
from fastapi import Request
from starlette.background import BackgroundTask
from starlette.responses import Response, StreamingResponse

from app.shared import discovery

# Cabeceras de un solo salto (RFC 9110 §7.6.1): no se reenvían.
_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
}

_balancer = discovery.RoundRobin()
_transport: httpx.AsyncBaseTransport | None = None
_client: httpx.AsyncClient | None = None


class Unavailable(Exception):
    def __init__(self, service: str):
        super().__init__(service)
        self.service = service


def set_network_transport(transport: httpx.AsyncBaseTransport | None) -> None:
    """Solo para pruebas: la red hacia las instancias que anuncia el directorio."""
    global _transport, _client
    _transport, _client = transport, None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(transport=_transport)
    return _client


def _has_body(request: Request) -> bool:
    return "content-length" in request.headers or "transfer-encoding" in request.headers


async def forward(service: str, request: Request) -> Response:
    try:
        base = await _balancer.pick(service)
    except discovery.NoInstances as exc:
        raise Unavailable(service) from exc

    headers = [(k, v) for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP]
    client_host = request.client.host if request.client else ""
    headers += [
        ("x-forwarded-for", client_host),
        ("x-forwarded-proto", request.url.scheme),
        ("x-forwarded-host", request.headers.get("host", "")),
    ]
    # La ruta tal como llegó: decodificarla y volver a codificarla cambia un %25 literal.
    url = f"{base}{request.scope['raw_path'].decode('latin-1')}"
    if request.url.query:
        url += f"?{request.url.query}"
    upstream_request = _http().build_request(
        request.method,
        url,
        headers=headers,
        content=request.stream() if _has_body(request) else None,
    )
    try:
        upstream = await _http().send(upstream_request, stream=True)
    except httpx.HTTPError as exc:
        raise Unavailable(service) from exc

    response = StreamingResponse(
        upstream.aiter_raw(),
        status_code=upstream.status_code,
        background=BackgroundTask(upstream.aclose),  # cierra la conexión aunque el cliente corte
    )
    # raw_headers conserva cabeceras repetidas (varios Set-Cookie).
    response.raw_headers = [
        (k.encode("latin-1"), v.encode("latin-1"))
        for k, v in upstream.headers.multi_items()
        if k.lower() not in _HOP_BY_HOP
    ]
    return response
