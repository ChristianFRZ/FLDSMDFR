"""Salud agregada: cada servicio responde en su `/internal/health`; la propia se calcula en proceso."""
import asyncio
import time

from sqlalchemy import text

from meloxo_common.db import session_scope
from meloxo_common.internal import UpstreamError

from playback_metrics.clients import catalog, users
from playback_metrics.modules.analytics import service
from playback_metrics.modules.analytics.aggregates import lag_seconds

MAX_LAG_SECONDS = 30


async def _remote(name: str, ask) -> dict:
    try:
        answer = await ask()
        return {**answer, "name": name}
    except Exception:  # cualquier fallo, incluido un cuerpo inesperado, es un servicio caído
        return {"name": name, "status": "down"}


async def _database() -> dict:
    try:
        started = time.perf_counter()
        async with session_scope() as session:
            await session.execute(text("SELECT 1"))
        return {"name": "database", "status": "up", "ms": round((time.perf_counter() - started) * 1000, 1)}
    except Exception:
        return {"name": "database", "status": "down"}


async def _jamendo() -> dict:
    try:
        return {"name": "jamendo", "status": await catalog.jamendo_status()}
    except UpstreamError:
        return {"name": "jamendo", "status": "down"}  # sin catálogo no se sabe nada de Jamendo


async def _aggregates(database: dict) -> dict:
    if database["status"] != "up":
        return {"name": "aggregates", "status": "down"}
    lag = await lag_seconds()
    return {
        "name": "aggregates",
        "status": "up" if lag is None or lag < MAX_LAG_SECONDS else "delayed",
        "lag_seconds": lag,
    }


async def health_report() -> list[dict]:
    """Las consultas a los otros servicios van a la vez: la página cuesta, como mucho, un tiempo de espera."""
    users_health, catalog_health, jamendo, database = await asyncio.gather(
        _remote("users-playlists", users.service_health),
        _remote("catalog-streaming", catalog.service_health),
        _jamendo(),
        _database(),
    )
    own = {"name": "playback-metrics", "status": "up", "uptime_seconds": service.uptime_seconds()}
    return [users_health, catalog_health, own, database, jamendo, await _aggregates(database)]
