"""Semilla idempotente del catálogo: canciones de media/seed/seed.json.

Los usuarios demo y el casete demo los crea la semilla de users-playlists, que resuelve
cada archivo contra este servicio por GET /internal/songs/lookup.
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
from app.shared.errors import DomainError

logger = logging.getLogger(__name__)


@dataclass
class SeedReport:
    songs_imported: int = 0
    songs_skipped: list[str] = field(default_factory=list)


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
        file_name = entry["file"]
        title, artist = entry["title"].strip(), entry["artist"].strip()
        album = entry["album"].strip() if isinstance(entry.get("album"), str) else ""
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
                album,
            )
        except DomainError as exc:
            logger.warning("Semilla: %s no es válido (%s); se omite", file_name, exc.message)
            report.songs_skipped.append(file_name)
            continue
        by_file[file_name] = song.id
        report.songs_imported += 1
    return by_file


async def run_seed(session: AsyncSession, seed_dir: Path) -> SeedReport:
    report = SeedReport()
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
    await _import_songs(session, seed_dir, entries, report)
    return report


async def _main() -> None:
    async with SessionLocal() as session:
        report = await run_seed(session, get_settings().seed_dir)
    print(
        f"Semilla del catálogo lista: {report.songs_imported} canciones importadas, "
        f"{len(report.songs_skipped)} omitidas {report.songs_skipped}"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
