"""Llamadas HTTP a otros servicios, por nombre lógico, balanceadas y con resiliencia.

Cada llamada pide al directorio (Consul, con caché de `lb_cache_s`) las instancias vivas del
servicio y elige una en round-robin, como el `@LoadBalanced` de Mexi Banco. Desde la rama 04:

- cada intento tiene un límite total de `call_timeout_s` (1.5 s);
- si falla por timeout, red o 5xx, se reintenta `retries` vez en OTRA instancia tras 100–300 ms
  (todas las llamadas internas son lecturas, así que reintentar no duplica nada);
- un circuit breaker por servicio remoto (app/shared/circuit.py) deja de llamar tras 5 llamadas
  fallidas seguidas y responde 503 al instante. Un 4xx no se reintenta ni cuenta: el dueño del
  dato sí respondió.
"""

import asyncio
import random

import httpx

from app.config import get_settings
from app.shared import discovery
from app.shared.circuit import CircuitBreaker, CircuitOpen
from app.shared.errors import DomainError, NotFound

_overrides: dict[str, httpx.AsyncBaseTransport] = {}
_override_clients: dict[str, httpx.AsyncClient] = {}
_network_transport: httpx.AsyncBaseTransport | None = None
_network: httpx.AsyncClient | None = None
_balancer = discovery.RoundRobin()
_breakers: dict[str, CircuitBreaker] = {}


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


def retry_wait() -> float:
    """Segundos de espera antes del reintento (aleatorio para no sincronizar reintentos)."""
    return random.uniform(0.1, 0.3)


def breakers() -> list[CircuitBreaker]:
    """Los circuitos de este proceso, para el endpoint de circuitos."""
    return list(_breakers.values())


def reset_breakers() -> None:
    """Solo para pruebas: olvida el estado de todos los circuitos."""
    _breakers.clear()


def _breaker(service: str) -> CircuitBreaker:
    breaker = _breakers.get(service)
    if breaker is None:
        settings = get_settings()
        breaker = CircuitBreaker(
            settings.service_name, service, settings.cb_failures, settings.cb_open_s
        )
        _breakers[service] = breaker
    return breaker


class _AttemptFailed(Exception):
    """Un intento falló de forma reintentable (timeout, red o 5xx)."""

    def __init__(self, base: str):
        self.base = base


async def _target(service: str, avoid: str | None) -> tuple[httpx.AsyncClient, str]:
    if service in _overrides:
        client = _override_clients.get(service)
        if client is None:
            client = httpx.AsyncClient(base_url=f"http://{service}", transport=_overrides[service])
            _override_clients[service] = client
        return client, ""
    global _network
    if _network is None:
        _network = httpx.AsyncClient(transport=_network_transport)
    base = await _balancer.pick(service)
    if avoid is not None and base == avoid:
        base = await _balancer.pick(service)  # el reintento va a otra instancia si la hay
    return _network, base


async def _attempt(
    service: str, method: str, path: str, avoid: str | None, **kwargs
) -> httpx.Response:
    client, base = await _target(service, avoid)
    timeout = get_settings().call_timeout_s
    try:
        async with asyncio.timeout(timeout):
            response = await client.request(method, f"{base}{path}", timeout=timeout, **kwargs)
    except (httpx.HTTPError, TimeoutError) as exc:
        raise _AttemptFailed(base) from exc
    if response.status_code >= 500:
        raise _AttemptFailed(base)
    return response


async def call(service: str, method: str, path: str, **kwargs) -> httpx.Response:
    """Hace la petición y traduce fallas: 404 → NotFound con el código remoto; red o 5xx → 503."""
    breaker = _breaker(service)
    try:
        breaker.before_call()
    except CircuitOpen as exc:
        raise RemoteUnavailable(service) from exc

    settled = False
    try:
        tried: str | None = None
        last: Exception | None = None
        for attempt in range(get_settings().retries + 1):
            if attempt:
                await asyncio.sleep(retry_wait())
            try:
                response = await _attempt(service, method, path, tried, **kwargs)
            except discovery.NoInstances as exc:  # reintentar no crea instancias
                last = exc
                break
            except _AttemptFailed as exc:
                tried, last = exc.base, exc
                continue
            breaker.record_success()
            settled = True
            return _translate(service, response)
        breaker.record_failure()
        settled = True
        raise RemoteUnavailable(service) from last
    finally:
        if not settled:
            breaker.abandon()


def _translate(service: str, response: httpx.Response) -> httpx.Response:
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
