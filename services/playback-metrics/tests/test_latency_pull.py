from datetime import UTC, datetime

from sqlalchemy import select

from meloxo_common.db import session_scope
from meloxo_common.latency import LatencyBucket
from playback_metrics import latency_pull
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
