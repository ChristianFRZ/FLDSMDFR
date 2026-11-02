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


async def test_like_and_list(user, session, media_dir):
    a = await insert_song(session, media_dir, title="A", seconds=2)
    b = await insert_song(session, media_dir, title="B", seconds=3)
    assert (await user.put(f"/api/me/favorites/{a.id}")).status_code == 204
    assert (await user.put(f"/api/me/favorites/{b.id}")).status_code == 204
    fav = (await user.get("/api/me/favorites")).json()
    assert [(s["title"], s["status"]) for s in fav["songs"]] == [("B", "ok"), ("A", "ok")]
    assert fav["total_seconds"] == 5


async def test_like_idempotent(user, session, media_dir):
    a = await insert_song(session, media_dir)
    await user.put(f"/api/me/favorites/{a.id}")
    assert (await user.put(f"/api/me/favorites/{a.id}")).status_code == 204
    assert len((await user.get("/api/me/favorites")).json()["songs"]) == 1


async def test_unlike_idempotent(user, session, media_dir):
    a = await insert_song(session, media_dir)
    await user.put(f"/api/me/favorites/{a.id}")
    assert (await user.delete(f"/api/me/favorites/{a.id}")).status_code == 204
    assert (await user.delete(f"/api/me/favorites/{a.id}")).status_code == 204
    assert (await user.get("/api/me/favorites")).json()["songs"] == []


async def test_like_unknown_song_404(user):
    r = await user.put(f"/api/me/favorites/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "song_not_found"


async def test_inactive_favorite_shown_unavailable(user, session, media_dir):
    a = await insert_song(session, media_dir)
    await user.put(f"/api/me/favorites/{a.id}")
    await catalog_service.deactivate_song(session, a.id)
    fav = (await user.get("/api/me/favorites")).json()
    assert fav["songs"][0]["status"] == "unavailable"
    assert fav["total_seconds"] == 0


async def test_favorites_per_user(user, client, session, media_dir):
    a = await insert_song(session, media_dir)
    await user.put(f"/api/me/favorites/{a.id}")
    other = AsyncClient(transport=client._transport, base_url="http://test")
    await signup(other, email="otra@test.mx")
    assert (await other.get("/api/me/favorites")).json()["songs"] == []
    await other.aclose()


async def test_ids_endpoint(user, session, media_dir):
    a = await insert_song(session, media_dir)
    await user.put(f"/api/me/favorites/{a.id}")
    assert (await user.get("/api/me/favorites/ids")).json() == [str(a.id)]
