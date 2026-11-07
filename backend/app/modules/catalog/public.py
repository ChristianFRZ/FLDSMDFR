"""Interfaz pública de modules.catalog. Solo tipos simples; cada función abre su sesión."""
import asyncio
import time
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.db import session_scope
from app.modules.catalog.import_jobs import refresh_metadata
from app.modules.catalog.jamendo import JamendoClient, JamendoError
from app.modules.catalog.models import Artist, Song
from app.modules.catalog.publishing import publish_due_tracks
from app.modules.catalog.schemas import ArtistSummary, PublishedRelease, ReleaseCounts, SongSummary, UpcomingRelease
from app.modules.catalog.service import to_artist_summary, to_summary
from app.modules.catalog.demo import DemoComposer, DemoTrack, ListenableSong, clear_demo_catalog, demo_import_done, import_demo_catalog, insert_demo_catalog, listenable_songs  # noqa: F401

JAMENDO_PING_SECONDS = 1.5
JAMENDO_STATUS_SECONDS = 60
_jamendo_status: dict[str, tuple[float, str]] = {}

__all__ = [
    "missing_song",
    "DemoComposer",
    "DemoTrack",
    "ListenableSong",
    "clear_demo_catalog",
    "demo_import_done",
    "import_demo_catalog",
    "insert_demo_catalog",
    "listenable_songs",
    "ArtistSummary",
    "PublishedRelease",
    "ReleaseCounts",
    "SongSummary",
    "UpcomingRelease",
    "catalog_by_source",
    "get_artists",
    "get_songs",
    "jamendo_status",
    "publish_due_tracks",
    "published_since",
    "refresh_metadata",
    "release_counts",
    "song_is_playable",
    "songs_owned_by",
    "upcoming_for_artists",
]


def missing_song(song_id: UUID) -> SongSummary:
    """Lo que muestra una lista de una pista que ya no existe y de la que no guardó metadatos."""
    return SongSummary(
        id=song_id,
        title="Pista eliminada",
        artist_id=UUID(int=0),
        artist="",
        album=None,
        duration=0,
        cover_url=None,
        source="local",
        license="",
        license_url=None,
        jamendo_url=None,
        genres=(),
        status="deleted",
        available=False,
    )


async def get_songs(ids: list[UUID]) -> dict[UUID, SongSummary]:
    if not ids:
        return {}
    async with session_scope() as session:
        rows = (await session.execute(select(Song).where(Song.id.in_(ids)))).unique().scalars()
        return {s.id: to_summary(s) for s in rows}


async def song_is_playable(song_id: UUID) -> bool:
    async with session_scope() as session:
        status = await session.scalar(select(Song.status).where(Song.id == song_id))
    return status == "published"


async def get_artists(ids: list[UUID]) -> dict[UUID, ArtistSummary]:
    if not ids:
        return {}
    async with session_scope() as session:
        rows = (await session.execute(select(Artist).where(Artist.id.in_(ids)))).scalars()
        return {a.id: to_artist_summary(a) for a in rows}


async def upcoming_for_artists(artist_ids: list[UUID]) -> list[UpcomingRelease]:
    if not artist_ids:
        return []
    query = (
        select(Song)
        .where(Song.artist_id.in_(artist_ids), Song.status == "scheduled", Song.publish_at.is_not(None))
        .order_by(Song.publish_at)
    )
    async with session_scope() as session:
        rows = (await session.execute(query)).unique().scalars()
        return [UpcomingRelease(s.id, s.title, s.artist_id, s.artist.name, s.publish_at) for s in rows]


async def published_since(artist_ids: list[UUID], since: datetime | None) -> list[PublishedRelease]:
    """Publicaciones de Compositores. Las importaciones de Jamendo no generan avisos."""
    if not artist_ids:
        return []
    filters = [Song.artist_id.in_(artist_ids), Song.status == "published", Song.source == "local"]
    if since is not None:
        filters.append(Song.published_at > since)
    query = select(Song).where(*filters).order_by(Song.published_at.desc()).limit(50)
    async with session_scope() as session:
        rows = (await session.execute(query)).unique().scalars()
        return [PublishedRelease(to_summary(s), s.published_at) for s in rows]


async def songs_owned_by(user_id: UUID) -> list[UUID]:
    query = select(Song.id).join(Artist, Song.artist_id == Artist.id).where(Artist.owner_user_id == user_id)
    async with session_scope() as session:
        return list((await session.execute(query)).scalars())


async def catalog_by_source() -> dict[str, int]:
    query = select(Song.source, func.count()).where(Song.status == "published").group_by(Song.source)
    async with session_scope() as session:
        return dict((await session.execute(query)).all())


async def release_counts(owner_id: UUID | None = None) -> ReleaseCounts:
    query = select(Song.status, func.count()).where(Song.source == "local").group_by(Song.status)
    if owner_id is not None:
        owned = select(Artist.id).where(Artist.owner_user_id == owner_id)
        query = query.where(Song.artist_id.in_(owned))
    async with session_scope() as session:
        counts = dict((await session.execute(query)).all())
    return ReleaseCounts(scheduled=counts.get("scheduled", 0), published=counts.get("published", 0))


async def _ask_jamendo() -> str:
    try:
        await asyncio.wait_for(JamendoClient().ping(), JAMENDO_PING_SECONDS)
    except TimeoutError:
        return "delayed"
    except JamendoError:
        return "down"
    return "up"


async def jamendo_status() -> str:
    """Se guarda un minuto: cada panel abierto pregunta cada 15 s y Jamendo es un servicio externo."""
    if not get_settings().JAMENDO_CLIENT_ID:
        return "not_configured"
    saved = _jamendo_status.get("value")
    if saved and time.monotonic() - saved[0] < JAMENDO_STATUS_SECONDS:
        return saved[1]
    status = await _ask_jamendo()
    _jamendo_status["value"] = (time.monotonic(), status)
    return status
