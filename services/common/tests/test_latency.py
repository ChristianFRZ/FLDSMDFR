from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI

from meloxo_common.latency import LatencyMiddleware, LatencyRecorder, internal_router


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 12, 10, 0, 30, tzinfo=UTC).timestamp()

    def __call__(self) -> float:
        return self.now


def classify(path: str) -> str | None:
    if path.startswith("/api/songs"):
        return "catalog"
    if path.startswith("/api/playlists"):
        return "playlists"
    return None


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def recorder(clock):
    return LatencyRecorder("catalog-service", classify, clock=clock)


def test_drain_returns_and_clears_buckets(recorder):
    recorder.record("/api/songs", 200, 0.010)
    recorder.record("/api/songs", 500, 0.030)
    [bucket] = recorder.drain()
    assert (bucket.service, bucket.module, bucket.count, bucket.errors) == ("catalog-service", "catalog", 2, 1)
    assert bucket.minute == datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
    assert (bucket.p50_ms, bucket.p95_ms) == (pytest.approx(10), pytest.approx(30))
    assert recorder.drain() == []


def test_buckets_group_by_module_and_minute(recorder, clock):
    recorder.record("/api/songs", 200, 0.01)
    recorder.record("/api/playlists", 200, 0.01)
    clock.now += 60
    recorder.record("/api/songs", 200, 0.01)
    keys = {(b.module, b.minute.minute): b.count for b in recorder.drain()}
    assert keys == {("catalog", 0): 1, ("playlists", 0): 1, ("catalog", 1): 1}


def test_classify_none_is_not_recorded(recorder):
    recorder.record("/assets/app.js", 200, 0.01)
    assert recorder.drain() == []


def test_percentiles_match_monolith(recorder):
    for ms in (10, 20, 30, 40):
        recorder.record("/api/songs", 200, ms / 1000)
    [bucket] = recorder.drain()
    assert (bucket.p50_ms, bucket.p95_ms) == (pytest.approx(20), pytest.approx(40))
    for ms in range(1, 101):
        recorder.record("/api/songs", 200, ms / 1000)
    [bucket] = recorder.drain()
    assert (bucket.p50_ms, bucket.p95_ms) == (pytest.approx(50), pytest.approx(95))
    recorder.record("/api/songs", 200, 0.007)
    [bucket] = recorder.drain()
    assert (bucket.p50_ms, bucket.p95_ms) == (pytest.approx(7), pytest.approx(7))


def build_app(recorder: LatencyRecorder) -> FastAPI:
    app = FastAPI()
    app.add_middleware(LatencyMiddleware, recorder=recorder)
    app.include_router(internal_router(recorder))

    @app.get("/api/songs")
    async def songs():
        return []

    @app.get("/api/playlists")
    async def playlists():
        raise RuntimeError("falla")

    return app


async def test_middleware_records_and_router_drains(recorder):
    app = build_app(recorder)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        assert (await client.get("/api/songs")).status_code == 200
        assert (await client.get("/api/playlists")).status_code == 500
        assert (await client.get("/otra")).status_code == 404
        response = await client.post("/internal/latency/drain")
        again = await client.post("/internal/latency/drain")
    items = {i["module"]: i for i in response.json()}
    assert set(items) == {"catalog", "playlists"}
    assert (items["catalog"]["count"], items["catalog"]["errors"]) == (1, 0)
    assert (items["playlists"]["count"], items["playlists"]["errors"]) == (1, 1)
    assert items["catalog"]["service"] == "catalog-service"
    assert items["catalog"]["minute"] == "2026-11-12T10:00:00Z"
    assert again.json() == []
