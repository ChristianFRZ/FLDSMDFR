import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.audio_fixtures import deactivate_song, insert_song, set_cover
from tests.helpers import signup

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
T0 = datetime(2026, 10, 1, 12, tzinfo=UTC)


@pytest.fixture
async def user(client):
    await signup(client)
    return client


async def _play(c, song_id, minutes=0):
    r = await c.post(
        "/api/playbacks",
        json={
            "playback_id": str(uuid.uuid4()),
            "song_id": str(song_id),
            "listened_seconds": 30,
            "occurred_at": (T0 + timedelta(minutes=minutes)).isoformat(),
        },
    )
    assert r.status_code == 201, r.text


async def test_history_dedupes_and_orders(user, session, media_dir):
    a = await insert_song(session, media_dir, title="A")
    b = await insert_song(session, media_dir, title="B")
    await _play(user, a.id, 0)
    await _play(user, b.id, 1)
    await _play(user, a.id, 2)
    page = (await user.get("/api/me/history")).json()
    assert page["total"] == 2
    assert [i["song"]["title"] for i in page["items"]] == ["A", "B"]
    assert page["items"][0]["available"] is True


async def test_history_is_per_user(user, client, session, media_dir):
    a = await insert_song(session, media_dir)
    await _play(user, a.id)
    other = AsyncClient(transport=client._transport, base_url="http://test")
    await signup(other, email="otra@test.mx")
    assert (await other.get("/api/me/history")).json() == {"items": [], "total": 0}
    await other.aclose()


async def test_history_marks_inactive_unavailable(user, session, media_dir):
    a = await insert_song(session, media_dir)
    await _play(user, a.id)
    await deactivate_song(a.id)
    item = (await user.get("/api/me/history")).json()["items"][0]
    assert item["available"] is False


async def test_history_paginates(user, session, media_dir):
    for i in range(3):
        s = await insert_song(session, media_dir, title=f"S{i}")
        await _play(user, s.id, i)
    page = (await user.get("/api/me/history?limit=2&offset=1")).json()
    assert page["total"] == 3
    assert [i["song"]["title"] for i in page["items"]] == ["S1", "S0"]
    assert (await user.get("/api/me/history?limit=51")).status_code == 422


async def test_top_artists_aggregates_and_counts_songs(user, session, media_dir):
    a1 = await insert_song(session, media_dir, title="A1", artist="Natalia Lafourcade")
    a2 = await insert_song(session, media_dir, title="A2", artist="natalia lafourcade")
    await insert_song(session, media_dir, title="A3", artist="Natalia Lafourcade")
    b = await insert_song(session, media_dir, title="B", artist="Masego")
    for s in (a1, a1, a2, b):
        await _play(user, s.id)
    top = (await user.get("/api/metrics/top-artists")).json()
    assert [(t["artist"], t["play_count"], t["song_count"]) for t in top] == [
        ("Natalia Lafourcade", 3, 3),
        ("Masego", 1, 1),
    ]
    assert top[0]["cover_song_id"] == str(a1.id)


async def test_top_artists_prefers_song_with_cover(user, client, session, media_dir):
    a1 = await insert_song(session, media_dir, title="A1", artist="Masego")
    a2 = await insert_song(session, media_dir, title="A2", artist="Masego")
    await _play(user, a1.id)
    await _play(user, a1.id, 1)
    await _play(user, a2.id, 2)
    await set_cover(a2.id)
    top = (await user.get("/api/metrics/top-artists")).json()
    assert top[0]["cover_song_id"] == str(a2.id)
