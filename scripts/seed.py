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
from app.modules.playlists import service as playlists_service
from app.modules.playlists.schemas import PlaylistIn
from app.modules.users import service as users_service
from app.shared.errors import DomainError

logger = logging.getLogger(__name__)


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


def _is_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_valid_entry(entry: object) -> bool:
    return isinstance(entry, dict) and all(
        _is_text(entry.get(k)) for k in ("file", "title", "artist")
    )


async def _import_songs(
    session: AsyncSession, seed_dir: Path, entries: list[dict], report: SeedReport
) -> dict[str, uuid.UUID]:
    """Devuelve archivo -> id de cancion para las que quedaron en el catalogo."""
    by_file: dict[str, uuid.UUID] = {}
    for index, entry in enumerate(entries, start=1):
        if not _is_valid_entry(entry):
            label = (
                entry["file"]
                if isinstance(entry, dict) and _is_text(entry.get("file"))
                else f"<entrada #{index}>"
            )
            logger.warning("Semilla: la entrada %s es inválida; se omite", label)
            report.songs_skipped.append(label)
            continue
        file_name, title, artist = entry["file"], entry["title"], entry["artist"]
        existing = await catalog_service.find_song_by_title_artist(session, title, artist)
        if existing is not None:
            if existing.is_active:
                by_file[file_name] = existing.id
            continue
        source = seed_dir / file_name
        if not source.is_file():
            logger.warning("Semilla: falta el archivo %s; se omite", file_name)
            report.songs_skipped.append(file_name)
            continue
        try:
            song = await catalog_service.import_song_file(
                session,
                source,
                title,
                artist,
                entry.get("album") if isinstance(entry.get("album"), str) else "",
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
    files, name = demo.get("files"), demo.get("name")
    if not isinstance(files, list) or not _is_text(name):
        logger.warning("Semilla: demo_playlist inválida; no se crea el casete")
        return
    song_ids = [by_file[f] for f in files if isinstance(f, str) and f in by_file]
    if not song_ids or await playlists_service.list_playlists(session, owner_id):
        return
    playlist = await playlists_service.create_playlist(session, owner_id, PlaylistIn(name=name))
    for song_id in song_ids:
        await playlists_service.add_song(session, owner_id, playlist.id, song_id)


async def run_seed(session: AsyncSession, seed_dir: Path) -> SeedReport:
    report = SeedReport()
    report.users_created, listener_id = await _ensure_users(session)
    manifest_path = seed_dir / "seed.json"
    if not manifest_path.is_file():
        logger.warning("Semilla: no existe %s; no se importan canciones", manifest_path)
        return report
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning(
            "Semilla: no se pudo leer %s (%s); no se importan canciones", manifest_path, exc
        )
        return report
    if not isinstance(manifest, dict):
        logger.warning("Semilla: %s no es un objeto JSON; no se importan canciones", manifest_path)
        return report
    entries = manifest.get("songs", [])
    if not isinstance(entries, list):
        logger.warning("Semilla: 'songs' no es una lista; no se importan canciones")
        entries = []
    by_file = await _import_songs(session, seed_dir, entries, report)
    demo = manifest.get("demo_playlist")
    if isinstance(demo, dict):
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
