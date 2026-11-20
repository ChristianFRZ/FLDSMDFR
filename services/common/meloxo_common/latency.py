"""Tiempo de respuesta por módulo: se acumula en memoria y se entrega al drenar.

El volcado a base de datos no está aquí: lo hace `playback-metrics` llamando al drenaje de cada servicio.
"""
import math
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Lock

from fastapi import APIRouter
from pydantic import BaseModel


class LatencyBucket(BaseModel):
    service: str
    module: str
    minute: datetime
    count: int
    errors: int
    p50_ms: float
    p95_ms: float


def _percentile(ordered: list[float], fraction: float) -> float:
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


class LatencyRecorder:
    def __init__(self, service: str, classify: Callable[[str], str | None], clock: Callable[[], float] = time.time):
        self.service = service
        self._classify = classify
        self._clock = clock
        self._lock = Lock()
        self._buffer: dict[tuple[datetime, str], tuple[list[float], int]] = defaultdict(lambda: ([], 0))

    def record(self, path: str, status: int, seconds: float) -> None:
        module = self._classify(path)
        if module is None:
            return
        minute = datetime.fromtimestamp(self._clock(), UTC).replace(second=0, microsecond=0)
        with self._lock:
            times, errors = self._buffer[(minute, module)]
            times.append(seconds * 1000)
            self._buffer[(minute, module)] = (times, errors + int(status >= 500))

    def drain(self) -> list[LatencyBucket]:
        """Devuelve todo lo acumulado y lo vacía; el intercambio es atómico bajo el candado."""
        with self._lock:
            taken, self._buffer = self._buffer, defaultdict(lambda: ([], 0))
        buckets = []
        for (minute, module), (times, errors) in sorted(taken.items()):
            ordered = sorted(times)
            buckets.append(
                LatencyBucket(
                    service=self.service,
                    module=module,
                    minute=minute,
                    count=len(ordered),
                    errors=errors,
                    p50_ms=_percentile(ordered, 0.5),
                    p95_ms=_percentile(ordered, 0.95),
                )
            )
        return buckets


class LatencyMiddleware:
    """ASGI puro para no almacenar el streaming. Mide hasta el primer byte, que es lo que siente quien escucha."""

    def __init__(self, app, recorder: LatencyRecorder):
        self.app = app
        self.recorder = recorder

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        recorded = False

        def finish(status: int) -> None:
            nonlocal recorded
            if not recorded:
                recorded = True
                self.recorder.record(scope["path"], status, time.perf_counter() - started)

        async def timed_send(message):
            if message["type"] == "http.response.start":
                finish(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, timed_send)
        except Exception:
            finish(500)
            raise


def internal_router(recorder: LatencyRecorder) -> APIRouter:
    router = APIRouter()

    @router.post("/internal/latency/drain", response_model=list[LatencyBucket])
    async def drain() -> list[LatencyBucket]:
        return recorder.drain()

    return router
