"""Contrato interno que consumen users-playlists y playback-metrics (sin sesión: red interna)."""

import uuid
from datetime import UTC, datetime, timedelta

from tests.audio_fixtures import insert_song


async def test_internal_get_song_404(client):
    r = await client.get(f"/internal/songs/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "song_not_found"


async def test_internal_get_song_without_session(client, session, media_dir):
    song = await insert_song(session, media_dir, title="Lluvia")
    r = await client.get(f"/internal/songs/{song.id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Lluvia"


async def test_internal_batch_includes_inactive_with_flag(client, session, media_dir):
    active = await insert_song(session, media_dir, title="Activa")
    inactive = await insert_song(session, media_dir, title="Retirada", is_active=False)
    r = await client.post(
        "/internal/songs/batch", json={"ids": [str(active.id), str(inactive.id)]}
    )
    assert r.status_code == 200
    flags = {s["title"]: s["is_active"] for s in r.json()}
    assert flags == {"Activa": True, "Retirada": False}


async def test_internal_count(client, session, media_dir):
    await insert_song(session, media_dir)
    await insert_song(session, media_dir, title="Otra")
    r = await client.get("/internal/songs/count")
    assert r.json() == {"count": 2}


async def test_internal_lookup_by_title_artist(client, session, media_dir):
    song = await insert_song(session, media_dir, title="Uno", artist="Banda A")
    r = await client.get("/internal/songs/lookup", params={"title": "uno", "artist": "BANDA A"})
    assert r.status_code == 200
    assert r.json()["id"] == str(song.id)
    missing = await client.get("/internal/songs/lookup", params={"title": "x", "artist": "y"})
    assert missing.status_code == 404


async def test_internal_artist_counts_normalized(client, session, media_dir):
    await insert_song(session, media_dir, artist="Los Meteoros")
    await insert_song(session, media_dir, title="B", artist="LOS METEOROS")
    r = await client.post("/internal/artists/counts", json={"artists": [" LOS METEOROS"]})
    assert r.json() == {"los meteoros": 2}


async def test_internal_artist_latest(client, session, media_dir):
    await insert_song(session, media_dir, title="Primera", artist="Banda")
    r = await client.post("/internal/artists/latest", json={"artists": ["Banda", "Nadie"]})
    body = r.json()
    assert list(body) == ["banda"]
    assert body["banda"]["title"] == "Primera"


async def test_internal_releases_respect_since(client, session, media_dir):
    await insert_song(session, media_dir, title="Nueva", artist="Banda")
    past = datetime.now(UTC) - timedelta(days=1)
    future = datetime.now(UTC) + timedelta(days=1)
    r = await client.post(
        "/internal/artists/releases",
        json={"follows": [{"artist": "banda", "since": past.isoformat()}],
              "not_before": past.isoformat()},
    )
    assert [s["title"] for s in r.json()] == ["Nueva"]
    later = await client.post(
        "/internal/artists/releases",
        json={"follows": [{"artist": "banda", "since": future.isoformat()}],
              "not_before": past.isoformat()},
    )
    assert later.json() == []


async def test_internal_count_includes_inactive(client, session, media_dir):
    """Contrato que replican los catálogos falsos de los otros servicios."""
    await insert_song(session, media_dir)
    await insert_song(session, media_dir, title="Retirada", is_active=False)
    assert (await client.get("/internal/songs/count")).json() == {"count": 2}
