"""Atajos para las pruebas heredadas del monolito: las canciones ahora viven en el catálogo
falso (tests/fake_catalog.py), no en una tabla de esta base."""

from pathlib import Path

from app.clients.catalog_schemas import SongOut
from tests.fake_catalog import FakeCatalog


async def insert_song(
    _session,
    _media_dir: Path,
    title: str = "Nubes de agosto",
    artist: str = "Los Meteoros",
    album: str = "Pronóstico",
    seconds: float = 2.0,
    is_active: bool = True,
) -> SongOut:
    fake = FakeCatalog.current
    song = fake.add_song(title, artist, album, duration_seconds=max(1, round(seconds)))
    if not is_active:
        fake.deactivate(song.id)
    return song


async def deactivate_song(song_id) -> None:
    FakeCatalog.current.deactivate(song_id)


async def set_cover(song_id) -> None:
    fake = FakeCatalog.current
    fake.songs[song_id] = fake.songs[song_id].model_copy(update={"has_cover": True})
