import asyncio
import time
import uuid

import pytest
from httpx import AsyncClient

from app.modules.catalog import service as catalog_service
from tests.audio_fixtures import insert_song
from tests.helpers import signup


@pytest.fixture
async def user(client):
    await signup(client)
    return client


async def _new_playlist(c, name="Mi casete") -> dict:
    r = await c.post("/api/playlists", json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()


async def _add(c, playlist_id, song_id):
    return await c.post(f"/api/playlists/{playlist_id}/songs", json={"song_id": str(song_id)})


async def test_create_and_list(user):
    created = await _new_playlist(user)
    assert created["name"] == "Mi casete"
    listing = (await user.get("/api/playlists")).json()
    assert [(p["id"], p["song_count"]) for p in listing] == [(created["id"], 0)]


async def test_add_song_and_get_detail(user, session, media_dir):
    a = await insert_song(session, media_dir, title="A", seconds=2)
    b = await insert_song(session, media_dir, title="B", seconds=3)
    pl = await _new_playlist(user)
    r1 = await _add(user, pl["id"], a.id)
    assert r1.status_code == 201, r1.text
    await _add(user, pl["id"], b.id)
    detail = (await user.get(f"/api/playlists/{pl['id']}")).json()
    assert [(s["title"], s["position"], s["status"]) for s in detail["songs"]] == [
        ("A", 1, "ok"),
        ("B", 2, "ok"),
    ]
    assert detail["total_seconds"] == 5
    assert (await user.get("/api/playlists")).json()[0]["song_count"] == 2


async def test_add_unknown_song_404(user):
    pl = await _new_playlist(user)
    r = await _add(user, pl["id"], uuid.uuid4())
    assert r.status_code == 404


async def test_add_duplicate_song_409(user, session, media_dir):
    a = await insert_song(session, media_dir)
    pl = await _new_playlist(user)
    assert (await _add(user, pl["id"], a.id)).status_code == 201
    r = await _add(user, pl["id"], a.id)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "song_already_in_playlist"


async def test_other_users_playlist_is_404(user, client, session, media_dir):
    a = await insert_song(session, media_dir)
    pl = await _new_playlist(user)
    async with AsyncClient(transport=client._transport, base_url="http://test") as other:
        await signup(other, email="otra@test.mx", name="Otra")
        assert (await other.get(f"/api/playlists/{pl['id']}")).status_code == 404
        assert (await _add(other, pl["id"], a.id)).status_code == 404
        assert (await other.get("/api/playlists")).json() == []


async def test_rename_playlist(user):
    pl = await _new_playlist(user)
    r = await user.patch(f"/api/playlists/{pl['id']}", json={"name": "Otro"})
    assert r.status_code == 200
    assert r.json()["name"] == "Otro"
    assert (await user.patch(f"/api/playlists/{pl['id']}", json={"name": ""})).status_code == 422
    assert (await user.patch(f"/api/playlists/{pl['id']}", json={"name": "   "})).status_code == 422
    assert (await user.post("/api/playlists", json={"name": "  \t "})).status_code == 422


async def test_remove_and_reorder(user, session, media_dir):
    a = await insert_song(session, media_dir, title="A")
    b = await insert_song(session, media_dir, title="B")
    c = await insert_song(session, media_dir, title="C")
    pl = await _new_playlist(user)
    for s in (a, b, c):
        await _add(user, pl["id"], s.id)

    r = await user.put(
        f"/api/playlists/{pl['id']}/order", json={"song_ids": [str(c.id), str(b.id), str(a.id)]}
    )
    assert r.status_code == 200, r.text
    assert [(s["title"], s["position"]) for s in r.json()["songs"]] == [
        ("C", 1),
        ("B", 2),
        ("A", 3),
    ]

    bad = await user.put(
        f"/api/playlists/{pl['id']}/order",
        json={"song_ids": [str(c.id), str(uuid.uuid4()), str(a.id)]},
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "invalid_order"
    partial = await user.put(f"/api/playlists/{pl['id']}/order", json={"song_ids": [str(c.id)]})
    assert partial.json()["error"]["code"] == "invalid_order"

    r = await user.delete(f"/api/playlists/{pl['id']}/songs/{b.id}")
    assert r.status_code == 200
    assert [(s["title"], s["position"]) for s in r.json()["songs"]] == [("C", 1), ("A", 2)]
    assert (await user.delete(f"/api/playlists/{pl['id']}/songs/{b.id}")).status_code == 404


async def test_deactivated_song_shows_unavailable(user, session, media_dir):
    a = await insert_song(session, media_dir, title="Vieja")
    pl = await _new_playlist(user)
    await _add(user, pl["id"], a.id)
    await catalog_service.deactivate_song(session, a.id)
    detail = (await user.get(f"/api/playlists/{pl['id']}")).json()
    assert detail["songs"][0]["status"] == "unavailable"
    assert detail["songs"][0]["title"] == "Vieja"


async def test_catalog_failure_degrades(user, session, media_dir, monkeypatch):
    a = await insert_song(session, media_dir, title="A", artist="X")
    b = await insert_song(session, media_dir, title="B", artist="Y")
    pl = await _new_playlist(user)
    await _add(user, pl["id"], a.id)
    await _add(user, pl["id"], b.id)

    async def boom(*args, **kwargs):
        raise RuntimeError("catálogo caído")

    monkeypatch.setattr("app.modules.catalog.service.get_songs_by_ids", boom)
    r = await user.get(f"/api/playlists/{pl['id']}")
    assert r.status_code == 200
    songs = r.json()["songs"]
    assert [(s["status"], s["title"], s["artist"]) for s in songs] == [
        ("degraded", "A", "X"),
        ("degraded", "B", "Y"),
    ]


async def test_get_playlist_under_200ms(user, session, media_dir):
    pl = await _new_playlist(user)
    for i in range(50):
        s = await insert_song(session, media_dir, title=f"Tema {i}", seconds=1)
        assert (await _add(user, pl["id"], s.id)).status_code == 201
    start = time.perf_counter()
    r = await user.get(f"/api/playlists/{pl['id']}")
    elapsed = time.perf_counter() - start
    assert r.status_code == 200
    assert len(r.json()["songs"]) == 50
    assert elapsed < 0.2


async def test_delete_playlist(user, session, media_dir):
    a = await insert_song(session, media_dir)
    pl = await _new_playlist(user)
    await _add(user, pl["id"], a.id)
    assert (await user.delete(f"/api/playlists/{pl['id']}")).status_code == 204
    assert (await user.get(f"/api/playlists/{pl['id']}")).status_code == 404


async def test_concurrent_adds_keep_positions_unique(user, session, media_dir):
    songs = [await insert_song(session, media_dir, title=f"T{i}") for i in range(5)]
    pl = await _new_playlist(user)
    responses = await asyncio.gather(*(_add(user, pl["id"], s.id) for s in songs))
    assert [r.status_code for r in responses] == [201] * 5
    detail = (await user.get(f"/api/playlists/{pl['id']}")).json()
    assert sorted(s["position"] for s in detail["songs"]) == [1, 2, 3, 4, 5]
