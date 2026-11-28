from uuid import uuid4

from tests.plays import record_play

from sqlalchemy import func, select

from meloxo_common.db import session_scope

from playback_metrics.modules.playback.models import Playback


async def _play(client, user, song_id):
    class Song:
        id = song_id

    return await record_play(user, Song)


async def _rows() -> int:
    async with session_scope() as session:
        return await session.scalar(select(func.count()).select_from(Playback))


async def test_playback_saved_when_catalog_down(client, listener, fake_catalog):
    song = fake_catalog.add_song()
    fake_catalog.down = True
    assert await _play(client, listener, song.id) == "created"
    assert await _rows() == 1


async def test_metrics_return_503_when_catalog_down(client, admin, fake_catalog):
    fake_catalog.down = True
    r = await client.get("/api/metrics/catalog-sources", headers=admin.headers)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "upstream_unavailable"
    r = await client.get("/api/metrics/top", headers=admin.headers)
    assert r.status_code == 200  # sin datos agregados no hace falta pedir nombres


async def test_top_returns_503_when_catalog_down_and_data_exists(client, admin, listener, fake_catalog):
    from playback_metrics.modules.analytics.aggregates import refresh_aggregates

    song = fake_catalog.add_song()
    await _play(client, listener, song.id)
    await refresh_aggregates(settle_seconds=0)
    fake_catalog.down = True
    r = await client.get("/api/metrics/top", headers=admin.headers)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "upstream_unavailable"


async def test_metrics_catalog_sources_uses_catalog_client(client, admin, fake_catalog):
    fake_catalog.add_song(source="jamendo", artist="R")
    r = await client.get("/api/metrics/catalog-sources", headers=admin.headers)
    assert r.json() == {"items": [{"source": "jamendo", "count": 1}]}
    assert [c.url.path for c in fake_catalog.calls] == ["/internal/catalog/by-source"]


async def test_inclusions_over_200_songs_sum_batches(client, composer, fake_catalog, fake_users):
    songs = [fake_catalog.add_song(title=f"P{i}", artist="Yo", owner=composer.id) for i in range(250)]
    fake_users.add_playlist(songs[:2])
    r = await client.get("/api/metrics/inclusions", headers=composer.headers)
    assert r.json() == {"playlists": 1, "tapes": 0}
    assert [len(c.url.params["song_ids"].split(",")) for c in fake_users.calls if "playlists" in c.url.path] == [200, 50]


async def test_auth_uses_users_service_and_survives_its_fall_via_cache(client, admin, fake_users):
    assert (await client.get("/api/metrics/duplicates", headers=admin.headers)).status_code == 200
    fake_users.down = True
    assert (await client.get("/api/metrics/duplicates", headers=admin.headers)).status_code == 200
