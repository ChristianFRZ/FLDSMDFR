"""Llamadas HTTP a otros servicios por la red de Compose (`http://<servicio>:8000`).

En 02-separacion no hay timeouts propios, reintentos ni circuit breaker (llegan en la rama
04): si el otro servicio no responde o falla con 5xx, la petición termina en un 503 uniforme.
"""

import httpx

from app.shared.errors import DomainError, NotFound

_clients: dict[str, httpx.AsyncClient] = {}
_transports: dict[str, httpx.AsyncBaseTransport | None] = {}


class RemoteUnavailable(DomainError):
    status = 503
    code = "service_unavailable"

    def __init__(self, service: str):
        super().__init__(
            f"El servicio {service} no está disponible. Intenta de nuevo en un momento."
        )
        self.service = service


def set_transport(base_url: str, transport: httpx.AsyncBaseTransport | None) -> None:
    """Solo para pruebas: sustituye la red real por un transporte (ASGI o simulado)."""
    _transports[base_url] = transport
    _clients.pop(base_url, None)


def get_client(base_url: str) -> httpx.AsyncClient:
    client = _clients.get(base_url)
    if client is None:
        client = httpx.AsyncClient(base_url=base_url, transport=_transports.get(base_url))
        _clients[base_url] = client
    return client


async def call(service: str, base_url: str, method: str, path: str, **kwargs) -> httpx.Response:
    """Hace la petición y traduce fallas: 404 → NotFound con el código remoto; red o 5xx → 503."""
    try:
        response = await get_client(base_url).request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        raise RemoteUnavailable(service) from exc
    if response.status_code == 404:
        error = _error_body(response)
        message = error.get("message", "No encontramos lo que buscas.")
        raise NotFound(message, code=error.get("code"))
    if response.status_code >= 400:
        raise RemoteUnavailable(service)
    return response


def _error_body(response: httpx.Response) -> dict:
    try:
        error = response.json().get("error", {})
    except ValueError:
        return {}
    return error if isinstance(error, dict) else {}
