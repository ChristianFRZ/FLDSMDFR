from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select

from meloxo_common.db import session_scope
from meloxo_common.latency import LatencyBucket
from playback_metrics import latency_pull
from playback_metrics.clients import catalog
from playback_metrics.config import get_settings
from playback_metrics.main import recorder
from playback_metrics.modules.analytics.models import RequestMetric

MINUTE = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def bucket(service, module, count, errors, p50, p95, minute=MINUTE) -> dict:
    return LatencyBucket(
        service=service, module=module, minute=minute, count=count, errors=errors, p50_ms=p50, p95_ms=p95
    ).model_dump(mode="json")


async def rows() -> dict[tuple[datetime, str], RequestMetric]:
    async with session_scope() as session:
        return {(r.minute, r.module): r for r in (await session.execute(select(RequestMetric))).scalars()}


async def test_pull_latency_writes_buckets_from_all_services(fake_users, fake_catalog):
    recorder.drain()
    fake_users.buckets = [bucket("users-playlists", "users", 4, 1, 10.0, 20.0)]
    fake_catalog.buckets = [bucket("catalog-streaming", "streaming", 6, 0, 30.0, 60.0)]
    recorder.record("/api/metrics/top", 200, 0.05)
    await latency_pull.pull_latency()
    found = await rows()
    modules = {module for _, module in found}
    assert modules == {"users", "streaming", "analytics"}
    assert found[(MINUTE, "users")].count == 4 and found[(MINUTE, "users")].errors == 1
    assert found[(MINUTE, "streaming")].p95_ms == 60.0
    own = next(r for (_, m), r in found.items() if m == "analytics")
    assert own.count == 1 and round(own.p50_ms) == 50


async def test_pull_latency_skips_unreachable_service_without_error(fake_users, fake_catalog):
    recorder.drain()
    fake_users.down = True
    fake_catalog.buckets = [bucket("catalog-streaming", "catalog", 3, 0, 5.0, 9.0)]
    await latency_pull.pull_latency()
    assert {module for _, module in await rows()} == {"catalog"}
    # users-playlists conserva sus buckets en memoria: cuando vuelve, se recogen
    fake_users.down = False
    fake_users.buckets = [bucket("users-playlists", "users", 2, 0, 1.0, 2.0)]
    await latency_pull.pull_latency()
    assert {module for _, module in await rows()} == {"catalog", "users"}


async def test_two_pulls_of_the_same_minute_are_merged_weighted_by_count(fake_users, fake_catalog):
    recorder.drain()
    fake_users.buckets = [bucket("users-playlists", "users", 1, 0, 10.0, 10.0)]
    await latency_pull.pull_latency()
    fake_users.buckets = [bucket("users-playlists", "users", 3, 1, 50.0, 90.0)]
    await latency_pull.pull_latency()
    row = (await rows())[(MINUTE, "users")]
    assert (row.count, row.errors) == (4, 1)
    assert row.p50_ms == (10.0 * 1 + 50.0 * 3) / 4
    assert row.p95_ms == (10.0 * 1 + 90.0 * 3) / 4


async def test_pull_latency_ignores_a_malformed_answer(fake_users, fake_catalog):
    recorder.drain()
    fake_users.buckets = [{"service": "users-playlists", "module": "users"}]
    await latency_pull.pull_latency()
    assert await rows() == {}


@pytest.fixture
def replicas(fake_catalog, monkeypatch):
    """Dos réplicas de catálogo detrás de un mismo nombre, con el puerto en `CATALOG_URL`."""
    monkeypatch.setattr(get_settings(), "CATALOG_URL", "http://catalog.test:8002")

    async def resolve():
        return ["10.0.0.1", "10.0.0.2"]

    monkeypatch.setattr(catalog, "resolve_replicas", resolve)
    return fake_catalog.add_replica("http://10.0.0.1:8002"), fake_catalog.add_replica("http://10.0.0.2:8002")


async def test_pull_latency_drains_every_replica(fake_users, replicas):
    recorder.drain()
    first, second = replicas
    first.buckets = [bucket("catalog-streaming", "catalog", 3, 0, 5.0, 9.0)]
    second.buckets = [bucket("catalog-streaming", "streaming", 7, 1, 6.0, 8.0)]
    await latency_pull.pull_latency()
    found = await rows()
    assert {module for _, module in found} == {"catalog", "streaming"}
    assert found[(MINUTE, "streaming")].count == 7


async def test_one_replica_down_keeps_the_other_buckets(fake_users, replicas):
    recorder.drain()
    first, second = replicas
    first.buckets = [bucket("catalog-streaming", "catalog", 3, 0, 5.0, 9.0)]
    second.error = httpx.ConnectError("réplica caída")
    await latency_pull.pull_latency()
    assert {module for _, module in await rows()} == {"catalog"}


async def test_single_name_still_works(fake_users, fake_catalog, monkeypatch):
    recorder.drain()
    monkeypatch.setattr(get_settings(), "CATALOG_URL", "http://catalog.test:8002")

    async def resolve():
        return ["10.0.0.1"]

    monkeypatch.setattr(catalog, "resolve_replicas", resolve)
    only = fake_catalog.add_replica("http://10.0.0.1:8002")
    only.buckets = [bucket("catalog-streaming", "catalog", 2, 0, 1.0, 2.0)]
    await latency_pull.pull_latency()
    assert {module for _, module in await rows()} == {"catalog"}
    assert [r.url.host for r in fake_catalog.calls] == ["10.0.0.1"]


async def test_invalid_answer_from_one_replica_keeps_the_other_buckets(fake_users, replicas):
    recorder.drain()
    first, second = replicas
    first.buckets = [bucket("catalog-streaming", "catalog", 3, 0, 5.0, 9.0)]
    second.buckets = [{"service": "catalog-streaming", "module": "streaming"}]
    await latency_pull.pull_latency()
    assert {module for _, module in await rows()} == {"catalog"}


async def test_stale_replica_clients_are_closed_and_evicted(fake_users, replicas, monkeypatch):
    first, second = replicas
    answers = iter([["10.0.0.1", "10.0.0.2"], ["10.0.0.1"]])

    async def resolve():
        return next(answers)

    monkeypatch.setattr(catalog, "resolve_replicas", resolve)
    await catalog.drain_latency_all()
    stale = catalog._replica_clients["10.0.0.2"]
    await catalog.drain_latency_all()
    assert set(catalog._replica_clients) == {"10.0.0.1"}
    assert stale._client.is_closed


async def test_resolve_replicas_returns_the_literal_ip(monkeypatch):
    monkeypatch.setattr(get_settings(), "CATALOG_URL", "http://10.1.2.3:8002")
    assert await catalog.resolve_replicas() == ["10.1.2.3"]


async def test_resolve_replicas_falls_back_to_the_host_on_dns_error(monkeypatch):
    monkeypatch.setattr(get_settings(), "CATALOG_URL", "http://catalog.invalid:8002")
    assert await catalog.resolve_replicas() == ["catalog.invalid"]
