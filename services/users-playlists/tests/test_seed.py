"""Semilla de users-playlists: usuarios demo y casete demo resuelto contra el catálogo."""

import json
from pathlib import Path

from app.config import get_settings
from app.modules.playlists import service as playlists_service
from app.modules.users import service as users_service
from scripts.seed import run_seed


def _write_seed(seed_dir: Path, songs: list, files: list) -> None:
    (seed_dir / "seed.json").write_text(
        json.dumps(
            {"songs": songs, "demo_playlist": {"name": "Para la tarde lluviosa", "files": files}}
        ),
        encoding="utf-8",
    )


async def _listener_id(session):
    settings = get_settings()
    user = await users_service.ensure_user(
        session, "Oyente", settings.listener_email, settings.listener_password, "listener"
    )
    return user.id


SONGS = [
    {"file": "uno.wav", "title": "Uno", "artist": "Banda A", "album": "Disco"},
    {"file": "dos.wav", "title": "Dos", "artist": "Banda B", "album": "Disco"},
]


async def test_seed_creates_users_and_demo_playlist_idempotently(session, catalog, tmp_path):
    catalog.add_song("Uno", "Banda A")
    catalog.add_song("Dos", "Banda B")
    _write_seed(tmp_path, SONGS, ["uno.wav", "dos.wav"])

    first = await run_seed(session, tmp_path)
    second = await run_seed(session, tmp_path)

    assert first.users_created == 2
    assert second.users_created == 0
    playlists = await playlists_service.list_playlists(session, await _listener_id(session))
    assert [(p.name, p.song_count) for p in playlists] == [("Para la tarde lluviosa", 2)]


async def test_seed_skips_files_missing_in_catalog(session, catalog, tmp_path):
    catalog.add_song("Uno", "Banda A")
    _write_seed(tmp_path, SONGS, ["uno.wav", "dos.wav"])

    await run_seed(session, tmp_path)

    playlists = await playlists_service.list_playlists(session, await _listener_id(session))
    assert playlists[0].song_count == 1


async def test_seed_without_songs_creates_no_playlist(session, tmp_path):
    _write_seed(tmp_path, [], [])
    report = await run_seed(session, tmp_path)
    assert report.users_created == 2
    assert await playlists_service.list_playlists(session, await _listener_id(session)) == []


async def test_seed_survives_invalid_manifest(session, tmp_path):
    (tmp_path / "seed.json").write_text("{ no es json", encoding="utf-8")
    report = await run_seed(session, tmp_path)
    assert report.users_created == 2


async def test_seed_survives_catalog_down(session, catalog_down, tmp_path):
    _write_seed(tmp_path, SONGS, ["uno.wav"])
    report = await run_seed(session, tmp_path)
    assert report.users_created == 2
    assert await playlists_service.list_playlists(session, await _listener_id(session)) == []
