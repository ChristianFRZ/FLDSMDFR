"""Semilla idempotente: usuarios iniciales, canciones de media/seed y casete demo.

Es un script de arranque (no un modulo de dominio): solo usa los servicios publicos.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import SessionLocal
from app.modules.catalog import service as catalog_service
from app.modules.catalog.schemas import SongOut
from app.modules.playlists import service as playlists_service
from app.modules.playlists.schemas import PlaylistIn
from app.modules.users import service as users_service
from app.shared.errors import DomainError

logger = logging.getLogger(__name__)

_SEARCH_LIMIT = 200


@dataclass
class SeedReport:
    users_created: int = 0
    songs_imported: int = 0
    songs_skipped: list[str] = field(default_factory=list)


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


async def _find_song(session: AsyncSession, title: str, artist: str) -> SongOut | None:
    page = await catalog_service.list_songs(session, title, limit=_SEARCH_LIMIT)
    return next((s for s in page.items if s.title == title and s.artist == artist), None)


async def _import_songs(
    session: AsyncSession, seed_dir: Path, entries: list[dict], report: SeedReport
) -> dict[str, uuid.UUID]:
    """Devuelve archivo -> id de cancion para las que quedaron en el catalogo."""
    by_file: dict[str, uuid.UUID] = {}
    for entry in entries:
        file_name, title, artist = entry["file"], entry["title"], entry["artist"]
        existing = await _find_song(session, title, artist)
        if existing is not None:
            by_file[file_name] = existing.id
            continue
        source = seed_dir / file_name
        if not source.is_file():
            logger.warning("Semilla: falta el archivo %s; se omite", file_name)
            report.songs_skipped.append(file_name)
            continue
        try:
            song = await catalog_service.import_song_file(
                session, source, title, artist, entry.get("album", "Sencillo")
            )
        except DomainError as exc:
            logger.warning("Semilla: %s no es válido (%s); se omite", file_name, exc.message)
            report.songs_skipped.append(file_name)
            continue
        by_file[file_name] = song.id
        report.songs_imported += 1
    return by_file


async def _ensure_demo_playlist(
    session: AsyncSession,
    owner_id: uuid.UUID,
    demo: dict,
    by_file: dict[str, uuid.UUID],
) -> None:
    song_ids = [by_file[f] for f in demo.get("files", []) if f in by_file]
    if not song_ids or await playlists_service.list_playlists(session, owner_id):
        return
    playlist = await playlists_service.create_playlist(
        session, owner_id, PlaylistIn(name=demo["name"])
    )
    for song_id in song_ids:
        await playlists_service.add_song(session, owner_id, playlist.id, song_id)


async def run_seed(session: AsyncSession, seed_dir: Path) -> SeedReport:
    report = SeedReport()
    report.users_created, listener_id = await _ensure_users(session)
    manifest_path = seed_dir / "seed.json"
    if not manifest_path.is_file():
        logger.warning("Semilla: no existe %s; no se importan canciones", manifest_path)
        return report
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_file = await _import_songs(session, seed_dir, manifest.get("songs", []), report)
    demo = manifest.get("demo_playlist")
    if demo:
        await _ensure_demo_playlist(session, listener_id, demo, by_file)
    return report


async def _main() -> None:
    async with SessionLocal() as session:
        report = await run_seed(session, get_settings().seed_dir)
    print(
        f"Semilla lista: {report.users_created} usuarios creados, "
        f"{report.songs_imported} canciones importadas, "
        f"{len(report.songs_skipped)} omitidas {report.songs_skipped}"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
