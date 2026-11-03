"""Llamadas HTTP a otros servicios, por nombre lógico y balanceadas del lado del cliente.

Cada llamada pide al directorio (Consul, con caché de `lb_cache_s`) las instancias vivas del
servicio y elige una en round-robin, como el `@LoadBalanced` de Mexi Banco. Todavía no hay
timeouts propios, reintentos en otra instancia ni circuit breaker (rama 04): si no hay
instancias, la elegida no responde o falla con 5xx, la petición termina en un 503 uniforme.
"""

import httpx

from app.shared import discovery
from app.shared.errors import DomainError, NotFound

_overrides: dict[str, httpx.AsyncBaseTransport] = {}
_override_clients: dict[str, httpx.AsyncClient] = {}
_network_transport: httpx.AsyncBaseTransport | None = None
_network: httpx.AsyncClient | None = None
_balancer = discovery.RoundRobin()


class RemoteUnavailable(DomainError):
    status = 503
    code = "service_unavailable"

    def __init__(self, service: str):
        super().__init__(
            f"El servicio {service} no está disponible. Intenta de nuevo en un momento."
        )
        self.service = service


def set_transport(service: str, transport: httpx.AsyncBaseTransport | None) -> None:
    """Solo para pruebas: atiende `service` con este transporte, sin pasar por el directorio."""
    _override_clients.pop(service, None)
    if transport is None:
        _overrides.pop(service, None)
    else:
        _overrides[service] = transport


def set_network_transport(transport: httpx.AsyncBaseTransport | None) -> None:
    """Solo para pruebas: la "red" hacia las instancias que devuelve el directorio."""
    global _network_transport, _network
    _network_transport, _network = transport, None


async def _target(service: str) -> tuple[httpx.AsyncClient, str]:
    if service in _overrides:
        client = _override_clients.get(service)
        if client is None:
            client = httpx.AsyncClient(base_url=f"http://{service}", transport=_overrides[service])
            _override_clients[service] = client
        return client, ""
    global _network
    if _network is None:
        _network = httpx.AsyncClient(transport=_network_transport)
    try:
        return _network, await _balancer.pick(service)
    except discovery.NoInstances as exc:
        raise RemoteUnavailable(service) from exc


async def call(service: str, method: str, path: str, **kwargs) -> httpx.Response:
    """Hace la petición y traduce fallas: 404 → NotFound con el código remoto; red o 5xx → 503."""
    client, base = await _target(service)
    try:
        response = await client.request(method, f"{base}{path}", **kwargs)
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
