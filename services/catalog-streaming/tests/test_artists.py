"""Consultas por artista que alimentan los avisos de lanzamientos de users-playlists."""

from datetime import UTC, datetime, timedelta

from app.modules.catalog import service as catalog_service
from tests.audio_fixtures import insert_song


async def test_songs_by_artists_since_ignores_older_and_inactive(session, media_dir):
    vieja = await insert_song(session, media_dir, title="Vieja", artist="Masego")
    since = datetime.now(UTC) + timedelta(milliseconds=1)
    nueva = await insert_song(session, media_dir, title="Nueva", artist="masego")
    inactiva = await insert_song(session, media_dir, title="Inactiva", artist="Masego")
    await catalog_service.deactivate_song(session, inactiva.id)
    await insert_song(session, media_dir, title="Otra", artist="Otro")
    songs = await catalog_service.songs_by_artists_since(
        session, [("masego", since)], not_before=since - timedelta(days=30)
    )
    assert [s.id for s in songs] == [nueva.id]
    assert vieja.id not in [s.id for s in songs]
