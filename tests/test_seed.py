import json
from pathlib import Path

from app.config import get_settings
from app.modules.catalog import service as catalog_service
from app.modules.playlists import service as playlists_service
from app.modules.users import service as users_service
from scripts.seed import run_seed
from tests.audio_fixtures import make_wav


def _write_seed(seed_dir: Path, songs: list[dict], files: list[str]) -> None:
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


async def test_seed_imports_and_is_idempotent(session, client, tmp_path):
    make_wav(tmp_path / "uno.wav")
    make_wav(tmp_path / "dos.wav")
    _write_seed(
        tmp_path,
        [
            {"file": "uno.wav", "title": "Uno", "artist": "Banda A", "album": "Disco"},
            {"file": "dos.wav", "title": "Dos", "artist": "Banda B", "album": "Disco"},
        ],
        ["uno.wav", "dos.wav"],
    )

    first = await run_seed(session, tmp_path)
    assert first.songs_imported == 2
    assert first.users_created == 2
    assert first.songs_skipped == []

    second = await run_seed(session, tmp_path)
    assert second.songs_imported == 0
    assert second.users_created == 0

    settings = get_settings()
    login = await client.post(
        "/api/auth/login",
        json={"email": settings.listener_email, "password": settings.listener_password},
    )
    assert login.status_code == 200
    songs = await client.get("/api/songs")
    assert songs.json()["total"] == 2

    owner = await _listener_id(session)
    playlists = await playlists_service.list_playlists(session, owner)
    assert len(playlists) == 1
    assert playlists[0].name == "Para la tarde lluviosa"
    assert playlists[0].song_count == 2


async def test_seed_skips_missing_files(session, tmp_path):
    _write_seed(
        tmp_path,
        [{"file": "falta.mp3", "title": "Falta", "artist": "Nadie", "album": "Nada"}],
        ["falta.mp3"],
    )

    report = await run_seed(session, tmp_path)

    assert report.songs_skipped == ["falta.mp3"]
    assert report.songs_imported == 0


async def test_seed_skips_invalid_files(session, tmp_path):
    (tmp_path / "roto.mp3").write_bytes(b"no soy audio")
    _write_seed(
        tmp_path,
        [{"file": "roto.mp3", "title": "Roto", "artist": "Nadie", "album": "Nada"}],
        [],
    )

    report = await run_seed(session, tmp_path)

    assert report.songs_skipped == ["roto.mp3"]


async def test_seed_with_empty_song_list(session, tmp_path):
    _write_seed(tmp_path, [], [])

    report = await run_seed(session, tmp_path)

    assert report.users_created == 2
    assert report.songs_imported == 0
    owner = await _listener_id(session)
    assert await playlists_service.list_playlists(session, owner) == []


async def test_seed_survives_invalid_manifest(session, tmp_path):
    (tmp_path / "seed.json").write_text("{ no es json", encoding="utf-8")

    report = await run_seed(session, tmp_path)

    assert report.users_created == 2
    assert report.songs_imported == 0


async def test_seed_skips_invalid_entries(session, tmp_path):
    make_wav(tmp_path / "bien.wav")
    make_wav(tmp_path / "mal.wav")
    _write_seed(
        tmp_path,
        [
            {"file": "mal.wav", "artist": "Nadie", "album": "Nada"},
            "no soy un objeto",
            {"file": "bien.wav", "title": "Bien", "artist": "Banda A", "album": "Disco"},
        ],
        ["bien.wav"],
    )

    report = await run_seed(session, tmp_path)

    assert report.songs_imported == 1
    assert report.songs_skipped == ["mal.wav", "<entrada #2>"]


async def test_seed_does_not_reimport_deactivated_songs(session, tmp_path):
    make_wav(tmp_path / "uno.wav")
    _write_seed(
        tmp_path,
        [{"file": "uno.wav", "title": "Uno", "artist": "Banda A", "album": "Disco"}],
        ["uno.wav"],
    )
    await run_seed(session, tmp_path)
    song = await catalog_service.find_song_by_title_artist(session, "uno", "BANDA A")
    assert song is not None
    await catalog_service.deactivate_song(session, song.id)

    report = await run_seed(session, tmp_path)

    assert report.songs_imported == 0
    assert (await catalog_service.list_songs(session, None)).total == 0
    again = await catalog_service.find_song_by_title_artist(session, "Uno", "Banda A")
    assert again is not None and again.is_active is False
