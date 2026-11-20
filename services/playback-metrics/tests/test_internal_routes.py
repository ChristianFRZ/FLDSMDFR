from uuid import uuid4

from sqlalchemy import func, select

from meloxo_common.db import session_scope
from playback_metrics.modules.playback.models import Playback


async def count_playbacks() -> int:
    async with session_scope() as session:
        return (await session.execute(select(func.count()).select_from(Playback))).scalar_one()


async def test_internal_health_has_the_common_shape(client):
    body = (await client.get("/internal/health")).json()
    assert body["name"] == "playback-metrics" and body["status"] == "up"
    assert isinstance(body["database_ms"], float) and isinstance(body["uptime_seconds"], int)


async def test_demo_playbacks_insert_and_clear_and_aggregates(client):
    play = {"user_id": str(uuid4()), "song_id": str(uuid4()), "listened_seconds": 90, "started_at": "2026-11-10T10:00:00Z"}
    assert (await client.post("/internal/demo/playbacks", json={"plays": [play], "duplicates": 3})).status_code == 204
    assert await count_playbacks() == 1
    assert (await client.post("/internal/demo/aggregates/rebuild")).status_code == 204
    assert (await client.post("/internal/demo/playbacks/clear")).status_code == 204
    assert await count_playbacks() == 0


async def test_demo_playbacks_rejects_a_malformed_body_in_api_format(client):
    response = await client.post("/internal/demo/playbacks", json={"plays": [{"user_id": "x"}]})
    assert response.status_code == 422 and "error" in response.json()


async def test_latency_drain_route_is_mounted(client):
    assert (await client.post("/internal/latency/drain")).status_code == 200
