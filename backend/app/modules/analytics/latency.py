"""Tiempo de respuesta por módulo. Se acumula en memoria y se vuelca a `request_metrics` por minuto."""
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert

from app.core.db import session_scope
from app.modules.analytics.models import RequestMetric

PREFIXES = (
    ("/api/admin/health", "analytics"),
    ("/api/admin/reports", "analytics"),
    ("/api/admin/catalog", "catalog"),
    ("/api/admin/songs", "catalog"),
    ("/api/admin", "users"),
    ("/api/auth", "users"),
    ("/api/users", "users"),
    ("/api/composer-requests", "users"),
    ("/api/composer", "catalog"),
    ("/api/songs", "catalog"),
    ("/api/artists", "catalog"),
    ("/api/genres", "catalog"),
    ("/api/media", "catalog"),
    ("/api/playlists", "playlists"),
    ("/api/playbacks", "playback"),
    ("/api/tapes", "social"),
    ("/api/favorites", "social"),
    ("/api/follows", "social"),
    ("/api/notices", "social"),
    ("/api/releases", "social"),
    ("/api/metrics", "analytics"),
)


def module_for(path: str) -> str | None:
    if path.startswith("/api/songs/") and path.endswith("/stream"):
        return "streaming"
    return next((module for prefix, module in PREFIXES if path.startswith(prefix)), None)


@dataclass
class Bucket:
    times: list[float] = field(default_factory=list)
    errors: int = 0


buffer: dict[tuple[datetime, str], Bucket] = defaultdict(Bucket)


def _minute() -> datetime:
    return datetime.now(UTC).replace(second=0, microsecond=0)


def record(module: str, milliseconds: float, failed: bool) -> None:
    bucket = buffer[(_minute(), module)]
    bucket.times.append(milliseconds)
    bucket.errors += int(failed)


def _percentile(ordered: list[float], fraction: float) -> float:
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


async def flush_latency(include_current: bool = False) -> None:
    """Vuelca los minutos ya cerrados. Si dos procesos escriben el mismo minuto, promedia por cantidad."""
    current = _minute()
    keys = [k for k in buffer if include_current or k[0] < current]
    if not keys:
        return
    async with session_scope() as session:
        for key in keys:
            bucket = buffer.pop(key)
            ordered = sorted(bucket.times)
            statement = insert(RequestMetric).values(
                minute=key[0],
                module=key[1],
                count=len(ordered),
                errors=bucket.errors,
                p50_ms=_percentile(ordered, 0.5),
                p95_ms=_percentile(ordered, 0.95),
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


class LatencyMiddleware:
    """ASGI puro para no almacenar el streaming. Mide hasta el primer byte, que es lo que siente quien escucha."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        module = module_for(scope["path"]) if scope["type"] == "http" else None
        if module is None:
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        recorded = False

        def finish(failed: bool) -> None:
            nonlocal recorded
            if not recorded:
                recorded = True
                record(module, (time.perf_counter() - started) * 1000, failed)

        async def timed_send(message):
            if message["type"] == "http.response.start":
                finish(message["status"] >= 500)
            await send(message)

        try:
            await self.app(scope, receive, timed_send)
        except Exception:
            finish(True)
            raise
