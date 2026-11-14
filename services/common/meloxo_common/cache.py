"""Caché de lectura en un Redis aparte (`CACHE_REDIS_URL`). Nunca lanza por culpa de Redis: sin caché o con la caché caída, `cached` llama al origen."""
import asyncio
import hashlib
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis

from meloxo_common.config import get_base_settings

log = logging.getLogger(__name__)

READ_TIMEOUT_SECONDS = 0.2
WRITE_TIMEOUT_SECONDS = 0.3
SKIP_AFTER_FAILURE_SECONDS = 5.0
_skip_until = 0.0
_client: Redis | None = None
_override: Redis | None = None
_FAILED = object()


def get_cache() -> Redis | None:
    if _override is not None:
        return _override
    global _client
    url = get_base_settings().CACHE_REDIS_URL
    if not url:
        return None
    if _client is None:
        _client = Redis.from_url(url, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=5)
    return _client


def override_cache(client: Redis | None) -> None:
    """Para pruebas: fija el cliente que devuelve `get_cache()`. `None` vuelve al de la URL."""
    global _override
    _override = client


def _available() -> Redis | None:
    client = get_cache()
    if client is None or time.monotonic() < _skip_until:
        return None
    return client


async def _run(operation: Awaitable[Any], timeout: float) -> Any:
    """Ejecuta una operación de la caché. Si falla o tarda, la salta unos segundos y devuelve `_FAILED`."""
    global _skip_until
    try:
        return await asyncio.wait_for(operation, timeout)
    except Exception as exc:
        _skip_until = time.monotonic() + SKIP_AFTER_FAILURE_SECONDS
        log.warning("La caché no respondió, se lee del origen: %s", type(exc).__name__)
        return _FAILED


def _version_key(namespace: str) -> str:
    return f"cache:ver:{namespace}"


def _key(namespace: str, params: dict, version: str | None) -> str:
    digest = hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()
    middle = f"{version}:" if version is not None else ""
    return f"cache:{namespace}:{middle}{digest}"


async def bump(namespace: str) -> None:
    """Sube la versión del espacio: lo guardado antes deja de consultarse. Nunca lanza."""
    client = _available()
    if client is not None:
        await _run(client.incr(_version_key(namespace)), WRITE_TIMEOUT_SECONDS)


async def cached(
    namespace: str,
    params: dict,
    ttl: int,
    loader: Callable[[], Awaitable[Any]],
    *,
    versioned: bool = False,
    should_store: Callable[[Any], bool] = lambda _: True,
) -> Any:
    """Devuelve lo guardado para `params` o carga y guarda. Si `loader` lanza, no se guarda nada.

    Con `versioned=True` la versión se lee una sola vez al principio: una escritura que ocurra mientras se
    carga deja el valor viejo bajo la versión vieja, que ya nadie consulta."""
    client = _available()
    if client is None:
        return await loader()
    version = None
    if versioned:
        raw = await _run(client.get(_version_key(namespace)), READ_TIMEOUT_SECONDS)
        if raw is _FAILED:
            return await loader()
        version = raw or "0"
    key = _key(namespace, params, version)
    hit = await _run(client.get(key), READ_TIMEOUT_SECONDS)
    if hit is not _FAILED and hit is not None:
        return json.loads(hit)
    value = await loader()
    if hit is not _FAILED and should_store(value) and _available() is not None:
        await _run(client.set(key, json.dumps(jsonable_encoder(value)), ex=ttl), WRITE_TIMEOUT_SECONDS)
    return value


async def get_json(key: str) -> Any | None:
    client = _available()
    if client is None:
        return None
    raw = await _run(client.get(key), READ_TIMEOUT_SECONDS)
    return None if raw is _FAILED or raw is None else json.loads(raw)


async def set_json(key: str, value: Any, ttl: int) -> None:
    client = _available()
    if client is not None:
        await _run(client.set(key, json.dumps(jsonable_encoder(value)), ex=ttl), WRITE_TIMEOUT_SECONDS)
