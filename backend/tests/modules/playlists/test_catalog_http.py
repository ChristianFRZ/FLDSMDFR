from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from app.catalog_main import app as catalog_app
from app.core.catalog_client import get_songs
from app.core.catalog_contract import BATCH_LIMIT, BATCH_PATH
from app.core.config import get_settings


@pytest.fixture
def remote(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "CATALOG_SERVICE_URL", "http://catalog-streaming-service:8080")
    monkeypatch.setattr(settings, "CATALOG_INTERNAL_TOKEN", SecretStr("token-de-prueba"))
    return settings.CATALOG_SERVICE_URL + BATCH_PATH


async def test_batch_private_and_validated(remote, client, listener, make_song):
    song = await make_song()
    batch = {"ids": [str(song.id), str(uuid4())]}
    assert (await client.post(BATCH_PATH, json=batch, headers=listener.headers)).status_code == 404
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=catalog_app), base_url="http://catalog") as catalog:
        for headers in ({}, listener.headers, {"X-Catalog-Token": "otro"}):
            assert (await catalog.post(BATCH_PATH, json=batch, headers=headers)).status_code == 403
        headers = {"X-Catalog-Token": "token-de-prueba"}
        response = await catalog.post(BATCH_PATH, json=batch, headers=headers)
        assert response.status_code == 200
        assert [s["id"] for s in response.json()["songs"]] == [str(song.id)]
        assert (await catalog.post(BATCH_PATH, json={"ids": ["inválido"]}, headers=headers)).status_code == 422
        assert (await catalog.get("/api/health")).json() == {"status": "ok"}


async def test_large_playlist_uses_bounded_batches(remote, respx_mock):
    route = respx_mock.post(remote).mock(return_value=httpx.Response(200, json={"songs": []}))
    assert await get_songs([uuid4() for _ in range(BATCH_LIMIT + 1)]) == {}
    assert route.call_count == 2
    assert route.calls.last.request.headers["X-Catalog-Token"] == "token-de-prueba"


async def test_http_outage_and_recovery(remote, respx_mock, client, listener, make_song):
    song = await make_song()
    playlist = (await client.post("/api/playlists", json={"name": "Viaje"}, headers=listener.headers)).json()
    path = f"/api/playlists/{playlist['id']}"
    body = {"song_id": str(song.id)}
    route = respx_mock.post(remote)
    # Las respuestas sanas vienen del endpoint real, con su autenticación y su consulta a PostgreSQL.
    route.mock(side_effect=httpx.ASGITransport(app=catalog_app).handle_async_request)
    assert (await client.post(path + "/songs", json=body, headers=listener.headers)).status_code == 201

    for failure in (httpx.ReadTimeout("tiempo agotado"), httpx.Response(404), httpx.Response(200, json={})):
        if isinstance(failure, Exception):
            route.mock(side_effect=failure)
        else:
            route.mock(return_value=failure)
        result = (await client.get(path, headers=listener.headers)).json()
        assert result["degraded"] and result["songs"][0]["title"] == song.title
        error = await client.post(path + "/songs", json=body, headers=listener.headers)
        assert error.status_code == 503
        assert error.json()["error"]["code"] == "catalog_unavailable"

    route.mock(side_effect=httpx.ASGITransport(app=catalog_app).handle_async_request)
    assert not (await client.get(path, headers=listener.headers)).json()["degraded"]
    unknown = await client.post(path + "/songs", json={"song_id": str(uuid4())}, headers=listener.headers)
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "song_not_found"
