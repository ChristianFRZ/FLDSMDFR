"""Semilla idempotente de users-playlists: usuarios demo y casete demo.

Las canciones las importa catalog-streaming. Aquí solo se lee `media/seed/seed.json` para
saber qué título y artista corresponden a cada archivo del casete demo, y cada uno se
resuelve contra el catálogo por HTTP (GET /internal/songs/lookup). Si el catálogo no
responde, se crean los usuarios y el casete se deja para el siguiente arranque.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import catalog
from app.clients.http import RemoteUnavailable
from app.config import get_settings
from app.db.session import SessionLocal
from app.modules.playlists import service as playlists_service
from app.modules.playlists.schemas import PlaylistIn
from app.modules.users import service as users_service

logger = logging.getLogger(__name__)


@dataclass
class SeedReport:
    users_created: int = 0
    demo_songs: int = 0


async def _ensure_users(session: AsyncSession) -> tuple[int, uuid.UUID]:
    settings = get_settings()
    before = await users_service.count_users(session)
    listener_id: uuid.UUID | None = None
    for name, email, password, role in (
        ("Administración", settings.admin_email, settings.admin_password, "admin"),
        ("Oyente", settings.listener_email, settings.listener_password, "listener"),
    ):
        user = await users_service.ensure_user(session, name, email, password, role)  # type: ignore[arg-type]
        if role == "listener":
            listener_id = user.id
    assert listener_id is not None
    return await users_service.count_users(session) - before, listener_id


def _read_manifest(seed_dir: Path) -> dict | None:
    path = seed_dir / "seed.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Semilla: no se pudo leer %s (%s); no se crea el casete demo", path, exc)
        return None
    return manifest if isinstance(manifest, dict) else None


def _titles_by_file(manifest: dict) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    songs = manifest.get("songs", [])
    for entry in songs if isinstance(songs, list) else []:
        if not isinstance(entry, dict):
            continue
        file, title, artist = entry.get("file"), entry.get("title"), entry.get("artist")
        if all(isinstance(v, str) and v.strip() for v in (file, title, artist)):
            out[file] = (title.strip(), artist.strip())
    return out


async def _ensure_demo_playlist(
    session: AsyncSession, owner_id: uuid.UUID, manifest: dict, report: SeedReport
) -> None:
    demo = manifest.get("demo_playlist")
    if not isinstance(demo, dict):
        return
    files, name = demo.get("files"), demo.get("name")
    if not isinstance(files, list) or not (isinstance(name, str) and name.strip()):
        logger.warning("Semilla: demo_playlist inválida; no se crea el casete")
        return
    if await playlists_service.list_playlists(session, owner_id):
        return
    titles = _titles_by_file(manifest)
    song_ids = []
    for file in files:
        if not isinstance(file, str) or file not in titles:
            continue
        song = await catalog.find_song_by_title_artist(*titles[file])
        if song is not None and song.is_active:
            song_ids.append(song.id)
    if not song_ids:
        return
    playlist = await playlists_service.create_playlist(session, owner_id, PlaylistIn(name=name))
    for song_id in song_ids:
        await playlists_service.add_song(session, owner_id, playlist.id, song_id)
    report.demo_songs = len(song_ids)


async def run_seed(session: AsyncSession, seed_dir: Path) -> SeedReport:
    report = SeedReport()
    report.users_created, listener_id = await _ensure_users(session)
    manifest = _read_manifest(seed_dir)
    if manifest is None:
        return report
    try:
        await _ensure_demo_playlist(session, listener_id, manifest, report)
    except RemoteUnavailable:
        logger.warning("Semilla: catalog-streaming no responde; el casete demo queda pendiente")
    return report


async def _main() -> None:
    async with SessionLocal() as session:
        report = await run_seed(session, get_settings().seed_dir)
    print(
        f"Semilla de users-playlists lista: {report.users_created} usuarios creados, "
        f"{report.demo_songs} canciones en el casete demo"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
