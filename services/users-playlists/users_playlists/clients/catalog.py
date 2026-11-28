"""Llamadas HTTP a catalog-streaming. Si ese servicio no responde, `UpstreamError` (503)."""
from datetime import datetime
from uuid import UUID

from meloxo_common.contracts import ArtistSummary, PublishedRelease, SongSummary, UpcomingRelease
from meloxo_common.internal import BATCH_SIZE, InternalClient

from users_playlists.config import get_settings

RECENT_LIMIT = 50  # el mismo tope que aplica catálogo a published_since

_client: InternalClient | None = None
_client_url: str | None = None


def _catalog() -> InternalClient:
    """Un cliente por URL: se vuelve a crear si cambia `CATALOG_URL`."""
    global _client, _client_url
    settings = get_settings()
    if _client is None or _client_url != settings.CATALOG_URL:
        _client = InternalClient(settings.CATALOG_URL, timeout=settings.INTERNAL_TIMEOUT_SECONDS)
        _client_url = settings.CATALOG_URL
    return _client


def _batches(ids: list[UUID]):
    for start in range(0, len(ids), BATCH_SIZE):
        yield ",".join(str(i) for i in ids[start : start + BATCH_SIZE])


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
    """Los ids que catálogo no conoce no aparecen en el resultado. Pide en lotes de 200 y une los diccionarios."""
    songs: dict[UUID, SongSummary] = {}
    for batch in _batches(list(dict.fromkeys(ids))):
        found = await _catalog().get("/internal/songs", ids=batch)
        songs.update({UUID(key): SongSummary.model_validate(value) for key, value in found.items()})
    return songs


async def get_artists(ids: list[UUID]) -> dict[UUID, ArtistSummary]:
    artists: dict[UUID, ArtistSummary] = {}
    for batch in _batches(list(dict.fromkeys(ids))):
        found = await _catalog().get("/internal/artists", ids=batch)
        artists.update({UUID(key): ArtistSummary.model_validate(value) for key, value in found.items()})
    return artists


async def upcoming_for_artists(artist_ids: list[UUID]) -> list[UpcomingRelease]:
    rows: list[UpcomingRelease] = []
    for batch in _batches(artist_ids):
        rows.extend(UpcomingRelease.model_validate(r) for r in await _catalog().get("/internal/artists/upcoming", artist_ids=batch))
    return sorted(rows, key=lambda r: r.publish_at)


async def published_since(artist_ids: list[UUID], since: datetime | None) -> list[PublishedRelease]:
    rows: list[PublishedRelease] = []
    for batch in _batches(artist_ids):
        found = await _catalog().get(
            "/internal/artists/published-since", artist_ids=batch, since=since.isoformat() if since else ""
        )
        rows.extend(PublishedRelease.model_validate(r) for r in found)
    return sorted(rows, key=lambda r: r.published_at, reverse=True)[:RECENT_LIMIT]


async def song_is_playable(song_id: UUID) -> bool:
    return (await _catalog().get(f"/internal/songs/{song_id}/playable"))["playable"]


async def songs_owned_by(user_id: UUID) -> list[UUID]:
    return [UUID(i) for i in await _catalog().get(f"/internal/owners/{user_id}/songs")]
