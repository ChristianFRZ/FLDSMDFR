"""Recolección de latencia: pide el drenaje a cada servicio y guarda los buckets en `request_metrics`."""
import asyncio
import logging

from pydantic import TypeAdapter
from sqlalchemy.dialects.postgresql import insert

from meloxo_common.db import session_scope
from meloxo_common.latency import LatencyBucket, LatencyRecorder

from playback_metrics.clients import catalog, users
from playback_metrics.modules.analytics.models import RequestMetric

log = logging.getLogger(__name__)
MODULE_LENGTH = 20  # tamaño de request_metrics.module
_buckets = TypeAdapter(list[LatencyBucket])


def module_for(path: str) -> str | None:
    if path.startswith("/api/playbacks"):
        return "playback"
    if path.startswith(("/api/metrics", "/api/admin/health", "/api/admin/reports")):
        return "analytics"
    return None


recorder = LatencyRecorder("playback-metrics", module_for)


async def _remote(name: str, drain) -> list[LatencyBucket]:
    """Si el servicio no responde, sus buckets esperan en su memoria. Si responde pero la respuesta del `drain` se pierde, esos buckets ya salieron de su memoria y se pierden."""
    try:
        return _buckets.validate_python(await drain())
    except Exception as exc:
        log.warning("No se pudo drenar la latencia de %s: %s", name, type(exc).__name__)
        return []


async def _store(buckets: list[LatencyBucket]) -> None:
    """Si dos volcados traen el mismo minuto, suma y promedia por cantidad. `drain()` incluye el minuto abierto."""
    if not buckets:
        return
    async with session_scope() as session:
        for item in buckets:
            statement = insert(RequestMetric).values(
                minute=item.minute,
                module=item.module[:MODULE_LENGTH],
                count=item.count,
                errors=item.errors,
                p50_ms=item.p50_ms,
                p95_ms=item.p95_ms,
            )
            new, old = statement.excluded, RequestMetric
            total = old.count + new.count
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[RequestMetric.minute, RequestMetric.module],
                    set_={
                        "count": total,
                        "errors": old.errors + new.errors,
                        "p50_ms": (old.p50_ms * old.count + new.p50_ms * new.count) / total,
                        "p95_ms": (old.p95_ms * old.count + new.p95_ms * new.count) / total,
                    },
                )
            )


async def pull_latency() -> None:
    from_users, from_catalog = await asyncio.gather(
        _remote("users-playlists", users.drain_latency),
        _remote("catalog-streaming", catalog.drain_latency_all),
    )
    own = recorder.drain()
    try:
        await _store([*from_users, *from_catalog, *own])
    except Exception:
        log.exception("No se pudieron guardar los buckets de latencia")
