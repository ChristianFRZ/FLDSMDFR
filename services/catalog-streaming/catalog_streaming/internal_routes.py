"""Rutas `/internal/*`: envoltorio fino sobre `modules/catalog/public.py`.

nginx no las publica y no llevan autenticación: solo las llaman otros servicios dentro de la red de Docker.
"""
import dataclasses
import time
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from sqlalchemy import text

from meloxo_common.contracts import ArtistSummary, PublishedRelease, ReleaseCounts, SongSummary, UpcomingRelease
from meloxo_common.db import session_scope

from catalog_streaming.modules.catalog import public

MAX_IDS = 200
router = APIRouter(prefix="/internal")
_started = time.monotonic()


def _uuids(raw: str) -> list[UUID]:
    """Lista separada por comas; vacía es válida. Más de 200 o un id mal formado dan 422."""
    return [UUID(part) for part in raw.split(",") if part]


def _parse(raw: str, field: str) -> list[UUID]:
    try:
        ids = _uuids(raw)
    except ValueError:
        raise RequestValidationError([{"loc": ("query", field), "msg": "Identificador no válido", "type": "value_error"}])
    if len(ids) > MAX_IDS:
        raise RequestValidationError(
            [{"loc": ("query", field), "msg": f"Máximo {MAX_IDS} identificadores", "type": "value_error"}]
        )
    return ids


def _song(summary) -> SongSummary:
    return SongSummary(**dataclasses.asdict(summary))


@router.get("/songs")
async def songs(ids: str = "") -> dict[UUID, SongSummary]:
    found = await public.get_songs(_parse(ids, "ids"))
    return {key: _song(value) for key, value in found.items()}


@router.get("/artists")
async def artists(ids: str = "") -> dict[UUID, ArtistSummary]:
    found = await public.get_artists(_parse(ids, "ids"))
    return {key: ArtistSummary(**dataclasses.asdict(value)) for key, value in found.items()}


@router.get("/songs/{song_id}/playable")
async def playable(song_id: UUID) -> dict[str, bool]:
    return {"playable": await public.song_is_playable(song_id)}


@router.get("/artists/upcoming")
async def upcoming(artist_ids: str = "") -> list[UpcomingRelease]:
    rows = await public.upcoming_for_artists(_parse(artist_ids, "artist_ids"))
    return [UpcomingRelease(**dataclasses.asdict(row)) for row in rows]


@router.get("/artists/published-since")
async def published_since(artist_ids: str = "", since: str = "") -> list[PublishedRelease]:
    when = datetime.fromisoformat(since) if since else None
    if when is not None and when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    rows = await public.published_since(_parse(artist_ids, "artist_ids"), when)
    return [PublishedRelease(song=_song(row.song), published_at=row.published_at) for row in rows]


@router.get("/owners/{user_id}/songs")
async def owned_songs(user_id: UUID) -> list[UUID]:
    return await public.songs_owned_by(user_id)


@router.get("/catalog/by-source")
async def by_source() -> dict[str, int]:
    return await public.catalog_by_source()


@router.get("/catalog/release-counts")
async def release_counts(owner_id: UUID | None = None) -> ReleaseCounts:
    counts = await public.release_counts(owner_id)
    return ReleaseCounts(**dataclasses.asdict(counts))


@router.get("/jamendo-status")
async def jamendo_status() -> dict[str, str]:
    return {"status": await public.jamendo_status()}


@router.get("/health")
async def health() -> dict:
    """Siempre 200: si la base no responde, `status` es `down` y `database_ms` es 0."""
    start = time.perf_counter()
    try:
        async with session_scope() as session:
            await session.execute(text("SELECT 1"))
        status, database_ms = "up", (time.perf_counter() - start) * 1000
    except Exception:
        status, database_ms = "down", 0.0
    return {
        "name": "catalog-streaming",
        "status": status,
        "database_ms": float(database_ms),
        "uptime_seconds": int(time.monotonic() - _started),
    }


class DemoTrackIn(BaseModel):
    title: str
    genre: str
    audio_path: str
    duration: float
    status: str
    publish_at: datetime | None = None
    published_at: datetime | None = None


class DemoComposerIn(BaseModel):
    user_id: UUID
    name: str
    bio: str
    tracks: list[DemoTrackIn]


class DemoCatalogIn(BaseModel):
    composers: list[DemoComposerIn]


class DemoImportIn(BaseModel):
    genres: list[str]
    per_genre: int


class DemoImportOut(BaseModel):
    status: str
    imported: int
    error: str | None


class ListenableOut(BaseModel):
    id: UUID
    artist_id: UUID
    duration: float
    source: str


@router.post("/demo/catalog", status_code=204)
async def insert_demo(body: DemoCatalogIn) -> None:
    await public.insert_demo_catalog(
        [
            public.DemoComposer(c.user_id, c.name, c.bio, [public.DemoTrack(**t.model_dump()) for t in c.tracks])
            for c in body.composers
        ]
    )


@router.post("/demo/catalog/clear", status_code=204)
async def clear_demo() -> None:
    await public.clear_demo_catalog()


@router.post("/demo/catalog/import")
async def import_demo(body: DemoImportIn) -> DemoImportOut:
    status, imported, error = await public.import_demo_catalog(body.genres, body.per_genre)
    return DemoImportOut(status=status, imported=imported, error=error)


@router.get("/demo/catalog/import-done")
async def import_done(genres: str = "", minimum: int = 0) -> dict[str, bool]:
    wanted = [g for g in genres.split(",") if g]
    return {"done": await public.demo_import_done(wanted, minimum)}


@router.get("/demo/catalog/listenable")
async def listenable(limit: int = 0) -> list[ListenableOut]:
    return [ListenableOut(**dataclasses.asdict(s)) for s in await public.listenable_songs(limit)]
