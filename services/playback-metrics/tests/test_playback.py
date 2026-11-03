import asyncio
import uuid

import pytest
from httpx import AsyncClient

from tests.audio_fixtures import deactivate_song, insert_song
from tests.helpers import make_admin_client, signup


@pytest.fixture
async def user(client):
    await signup(client)
    return client


def _event(song_id, playback_id=None, seconds=30) -> dict:
    return {
        "playback_id": str(playback_id or uuid.uuid4()),
        "song_id": str(song_id),
        "listened_seconds": seconds,
    }


async def _top(c: AsyncClient) -> list[dict]:
    r = await c.get("/api/metrics/top")
    assert r.status_code == 200, r.text
    return r.json()


async def test_first_event_counts(user, session, media_dir):
    song = await insert_song(session, media_dir)
    r = await user.post("/api/playbacks", json=_event(song.id))
    assert r.status_code == 201
    assert r.json()["counted"] is True
    top = await _top(user)
    assert [(t["song_id"], t["play_count"]) for t in top] == [(str(song.id), 1)]


async def test_retry_same_id_not_double_counted(user, session, media_dir):
    song = await insert_song(session, media_dir)
    body = _event(song.id)
    assert (await user.post("/api/playbacks", json=body)).status_code == 201
    again = await user.post("/api/playbacks", json=body)
    assert again.status_code == 200
    assert again.json()["counted"] is False
    assert (await _top(user))[0]["play_count"] == 1


async def test_concurrent_same_id_counts_once(user, session, media_dir):
    song = await insert_song(session, media_dir)
    body = _event(song.id)
    # Cada peticion abre su propia sesion de DB (get_session).
    responses = await asyncio.gather(*(user.post("/api/playbacks", json=body) for _ in range(5)))
    assert sorted(r.status_code for r in responses) == [200, 200, 200, 200, 201]
    assert (await _top(user))[0]["play_count"] == 1


async def test_concurrent_distinct_ids(user, session, media_dir):
    song = await insert_song(session, media_dir)
    responses = await asyncio.gather(
        *(user.post("/api/playbacks", json=_event(song.id)) for _ in range(20))
    )
    assert [r.status_code for r in responses] == [201] * 20
    assert (await _top(user))[0]["play_count"] == 20


@pytest.mark.parametrize("seconds", [9, 86401])
async def test_listened_seconds_out_of_range_rejected(user, session, media_dir, seconds):
    song = await insert_song(session, media_dir)
    r = await user.post("/api/playbacks", json=_event(song.id, seconds=seconds))
    assert r.status_code == 422


async def test_unknown_song_404(user):
    r = await user.post("/api/playbacks", json=_event(uuid.uuid4()))
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "song_not_found"


async def test_requires_session(client):
    r = await client.post("/api/playbacks", json=_event(uuid.uuid4()))
    assert r.status_code == 401


async def test_top_ordering(user, session, media_dir):
    a = await insert_song(session, media_dir, title="A")
    b = await insert_song(session, media_dir, title="B")
    for _ in range(3):
        await user.post("/api/playbacks", json=_event(a.id))
    await user.post("/api/playbacks", json=_event(b.id))
    top = await _top(user)
    assert [(t["title"], t["play_count"]) for t in top] == [("A", 3), ("B", 1)]


async def test_top_limit_validated_and_applied(user, session, media_dir):
    a = await insert_song(session, media_dir, title="A")
    b = await insert_song(session, media_dir, title="B")
    await user.post("/api/playbacks", json=_event(a.id))
    await user.post("/api/playbacks", json=_event(b.id))
    assert len((await user.get("/api/metrics/top?limit=1")).json()) == 1
    assert (await user.get("/api/metrics/top?limit=0")).status_code == 422
    assert (await user.get("/api/metrics/top?limit=51")).status_code == 422


async def test_top_skips_deactivated_song(user, session, media_dir):
    a = await insert_song(session, media_dir, title="A")
    b = await insert_song(session, media_dir, title="B")
    await user.post("/api/playbacks", json=_event(a.id))
    await user.post("/api/playbacks", json=_event(b.id))
    await deactivate_song(a.id)
    assert [t["title"] for t in await _top(user)] == ["B"]


async def test_top_degraded_when_catalog_fails(user, session, media_dir, take_down):
    a = await insert_song(session, media_dir, title="A")
    await user.post("/api/playbacks", json=_event(a.id))

    take_down("catalog-streaming")
    top = await _top(user)
    assert [(t["song_id"], t["title"], t["play_count"]) for t in top] == [
        (str(a.id), "Canción no disponible", 1)
    ]


async def test_summary_admin_only(user, session, media_dir, users):
    song = await insert_song(session, media_dir)
    await user.post("/api/playbacks", json=_event(song.id))
    await user.post("/api/playbacks", json=_event(song.id))
    assert (await user.get("/api/metrics/summary")).status_code == 403
    users.count = 2
    admin = await make_admin_client(session, user)
    r = await admin.get("/api/metrics/summary")
    assert r.status_code == 200
    body = r.json()
    assert (body["total_playbacks"], body["total_songs"], body["total_users"]) == (2, 1, 2)
    assert [(t["song_id"], t["play_count"]) for t in body["top"]] == [(str(song.id), 2)]


async def test_top_includes_full_song_for_playback(user, session, media_dir):
    """La página de inicio reproduce desde el top: necesita duración y portada."""
    song = await insert_song(session, media_dir)
    await user.post("/api/playbacks", json=_event(song.id))
    [item] = await _top(user)
    assert item["song"]["id"] == str(song.id)
    assert item["song"]["duration_seconds"] == song.duration_seconds
    assert item["song"]["has_cover"] is False


async def test_summary_total_songs_counts_inactive(user, session, media_dir, users):
    """Igual que el catálogo real (y el monolito): total_songs cuenta también las retiradas."""
    song = await insert_song(session, media_dir)
    await insert_song(session, media_dir, title="Otra")
    await deactivate_song(song.id)
    admin = await make_admin_client(session, user)
    body = (await admin.get("/api/metrics/summary")).json()
    assert body["total_songs"] == 2
