"""Directorio de servicios (Consul): registro con latido, baja y búsqueda de instancias.

Cada instancia se registra al arrancar con su nombre lógico, un id único (<servicio>-<host>),
su IP y un check TTL. Después manda un latido cada `heartbeat_s`. Si deja de mandarlo, Consul
marca el check `critical` a los `ttl_s` segundos: la instancia deja de aparecer en
`?passing=true` y, pasado `deregister_after`, sale del registro. Al apagarse en orden se da de
baja sola. Es el mismo modelo de latido y expiración que Eureka en el curso.

Quien busca instancias (gateway o clientes internos) guarda la lista `lb_cache_s` segundos:
por eso una réplica muerta puede seguir recibiendo tráfico hasta ttl_s + lb_cache_s.
"""

import asyncio
import contextlib
import logging
import socket
import time

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_transport: httpx.AsyncBaseTransport | None = None
_client: httpx.AsyncClient | None = None
_registered: dict | None = None  # cuerpo del registro de esta instancia
_heartbeat: asyncio.Task | None = None
_cache: dict[str, tuple[float, list[str]]] = {}


class NoInstances(Exception):
    def __init__(self, service: str):
        super().__init__(f"No hay instancias vivas de {service}")
        self.service = service


def set_consul_transport(transport: httpx.AsyncBaseTransport | None) -> None:
    """Solo para pruebas: sustituye la red hacia Consul."""
    global _transport, _client
    _transport, _client = transport, None


def reset() -> None:
    """Solo para pruebas: olvida el registro, la caché y la tarea de latido."""
    global _registered, _heartbeat
    if _heartbeat is not None:
        _heartbeat.cancel()
    _registered, _heartbeat = None, None
    _cache.clear()


def _consul() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=get_settings().consul_url, transport=_transport, timeout=2.0
        )
    return _client


def instance_id() -> str:
    return f"{get_settings().service_name}-{socket.gethostname()}"


def _address() -> str:
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


async def _put_registration() -> bool:
    assert _registered is not None
    try:
        r = await _consul().put("/v1/agent/service/register", json=_registered)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Directorio: no se pudo registrar %s (%s)", _registered["ID"], exc)
        return False
    logger.info("Directorio: registrada %s en %s", _registered["ID"], _registered["Address"])
    return True


async def register(name: str, port: int, start_heartbeat: bool = True) -> str:
    """Registra esta instancia. Si el directorio no responde, el latido reintentará."""
    global _registered, _heartbeat
    settings = get_settings()
    instance = f"{name}-{socket.gethostname()}"
    _registered = {
        "ID": instance,
        "Name": name,
        "Address": _address(),
        "Port": port,
        "Check": {
            "CheckID": f"{instance}-ttl",
            "TTL": f"{settings.ttl_s}s",
            "DeregisterCriticalServiceAfter": settings.deregister_after,
        },
    }
    if await _put_registration():
        await heartbeat_once()
    if start_heartbeat:
        _heartbeat = asyncio.create_task(_heartbeat_loop(settings.heartbeat_s))
    return instance


async def heartbeat_once() -> None:
    """Un latido. Si Consul ya no conoce el check (se reinició o nos expulsó), se re-registra."""
    if _registered is None:
        return
    address = _address()
    if address != _registered["Address"]:
        # Docker le cambió la IP a este contenedor vivo: sin esto, el directorio seguiría
        # anunciando una IP que ahora puede ser de otro servicio.
        logger.warning(
            "Directorio: la IP de %s cambió de %s a %s; se vuelve a registrar",
            _registered["ID"],
            _registered["Address"],
            address,
        )
        _registered["Address"] = address
        if not await _put_registration():
            return
    check = _registered["Check"]["CheckID"]
    try:
        r = await _consul().put(f"/v1/agent/check/pass/{check}")
    except httpx.HTTPError as exc:
        logger.warning("Directorio: latido fallido (%s)", exc)
        return
    if r.status_code >= 400:
        await _put_registration()


async def _heartbeat_loop(every_s: float) -> None:
    while True:
        await asyncio.sleep(every_s)
        await heartbeat_once()


async def deregister() -> None:
    """Baja ordenada (SIGTERM): el directorio deja de anunciar esta instancia de inmediato."""
    global _registered, _heartbeat
    if _heartbeat is not None:
        _heartbeat.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _heartbeat
        _heartbeat = None
    if _registered is not None:
        with contextlib.suppress(httpx.HTTPError):
            await _consul().put(f"/v1/agent/service/deregister/{_registered['ID']}")
        logger.info("Directorio: baja de %s", _registered["ID"])
    _registered = None


async def instances(name: str, use_cache: bool = True) -> list[str]:
    """URLs base de las instancias vivas (`passing`) de `name`, con caché de `lb_cache_s`."""
    now = time.monotonic()
    cached = _cache.get(name)
    if use_cache and cached is not None and cached[0] > now:
        return cached[1]
    try:
        r = await _consul().get(f"/v1/health/service/{name}", params={"passing": "true"})
        r.raise_for_status()
        urls = [f"http://{e['Service']['Address']}:{e['Service']['Port']}" for e in r.json()]
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("Directorio: no se pudo consultar %s (%s)", name, exc)
        urls = []
    _cache[name] = (now + get_settings().lb_cache_s, urls)
    return urls


class RoundRobin:
    """Balanceador round-robin sobre la lista (cacheada) del directorio, por servicio."""

    def __init__(self) -> None:
        self._next: dict[str, int] = {}

    async def pick(self, name: str) -> str:
        urls = await instances(name)
        if not urls:
            raise NoInstances(name)
        i = self._next.get(name, 0)
        self._next[name] = i + 1
        return urls[i % len(urls)]
