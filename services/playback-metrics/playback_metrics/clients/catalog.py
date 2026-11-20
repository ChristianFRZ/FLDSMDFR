"""Llamadas HTTP a catalog-streaming. Si ese servicio no responde, `UpstreamError` (503)."""
from uuid import UUID

from meloxo_common.contracts import ArtistSummary, ReleaseCounts, SongSummary
from meloxo_common.internal import BATCH_SIZE, InternalClient

from playback_metrics.config import get_settings

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


async def catalog_by_source() -> dict[str, int]:
    return await _catalog().get("/internal/catalog/by-source")


async def release_counts(owner_id: UUID | None = None) -> ReleaseCounts:
    params = {"owner_id": str(owner_id)} if owner_id else {}
    return ReleaseCounts.model_validate(await _catalog().get("/internal/catalog/release-counts", **params))


async def jamendo_status() -> str:
    return (await _catalog().get("/internal/jamendo-status"))["status"]


async def songs_owned_by(user_id: UUID) -> list[UUID]:
    return [UUID(i) for i in await _catalog().get(f"/internal/owners/{user_id}/songs")]


async def service_health() -> dict:
    return await _catalog().get("/internal/health")


async def drain_latency() -> list[dict]:
    return await _catalog().post("/internal/latency/drain")
