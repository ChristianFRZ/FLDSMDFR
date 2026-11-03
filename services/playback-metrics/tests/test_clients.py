"""playback-metrics depende por HTTP de catalog-streaming y de users-playlists."""

import uuid

import pytest
from httpx import AsyncClient

from tests.audio_fixtures import insert_song
from tests.helpers import make_admin_client, signup


@pytest.fixture
async def user(client: AsyncClient) -> AsyncClient:
    await signup(client)
    return client


def _event(song_id) -> dict:
    return {"playback_id": str(uuid.uuid4()), "song_id": str(song_id), "listened_seconds": 12}


async def test_record_playback_unknown_song_404(user):
    r = await user.post("/api/playbacks", json=_event(uuid.uuid4()))
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "song_not_found"


async def test_record_playback_catalog_down_503(user, session, media_dir, take_down):
    song = await insert_song(session, media_dir)
    take_down("catalog-streaming")
    r = await user.post("/api/playbacks", json=_event(song.id))
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "service_unavailable"
    assert "catalog-streaming" in r.json()["error"]["message"]


async def test_summary_users_down_503(client, session, take_down):
    admin = await make_admin_client(session, client)
    take_down("users-playlists")
    r = await admin.get("/api/metrics/summary")
    assert r.status_code == 503
    assert "users-playlists" in r.json()["error"]["message"]
    await admin.aclose()


async def test_empty_history_needs_no_catalog(user, take_down):
    """Con historial vacío no se llama al catálogo; con datos responde 503 (lo mejora 04)."""
    take_down("catalog-streaming")
    r = await user.get("/api/me/history")
    assert r.status_code == 200  # historial vacío: no hay ids que pedirle al catálogo
