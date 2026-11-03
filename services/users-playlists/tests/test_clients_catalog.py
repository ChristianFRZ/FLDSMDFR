"""Las llamadas a catalog-streaming viajan por HTTP: qué ve quien usa la API cuando falla."""

import uuid

import httpx
import pytest
from httpx import AsyncClient

from app.clients import http as remote
from tests.helpers import signup


@pytest.fixture
async def user(client: AsyncClient) -> AsyncClient:
    await signup(client)
    return client


async def _playlist(user: AsyncClient) -> str:
    r = await user.post("/api/playlists", json={"name": "Lluvia"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_get_song_404_maps_to_song_not_found(user):
    playlist_id = await _playlist(user)
    r = await user.post(f"/api/playlists/{playlist_id}/songs", json={"song_id": str(uuid.uuid4())})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "song_not_found"


async def test_catalog_down_returns_503(user, catalog_down):
    playlist_id = await _playlist(user)
    r = await user.post(f"/api/playlists/{playlist_id}/songs", json={"song_id": str(uuid.uuid4())})
    assert r.status_code == 503
    body = r.json()["error"]
    assert body["code"] == "service_unavailable"
    assert "catalog-streaming" in body["message"]


async def test_catalog_5xx_returns_503(user, catalog):
    async def boom(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"code": "internal", "message": "x"}})

    remote.set_transport("http://catalog.test", httpx.MockTransport(boom))
    r = await user.put(f"/api/me/favorites/{uuid.uuid4()}")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "service_unavailable"


async def test_playlist_detail_degrades_when_catalog_down(user, catalog, catalog_down):
    """Comportamiento heredado del monolito: el casete se muestra con sus copias guardadas."""
    playlist_id = await _playlist(user)
    r = await user.get(f"/api/playlists/{playlist_id}")
    assert r.status_code == 200


async def test_playlists_list_works_without_catalog(user, catalog_down):
    await _playlist(user)
    r = await user.get("/api/playlists")
    assert r.status_code == 200
    assert len(r.json()) == 1
