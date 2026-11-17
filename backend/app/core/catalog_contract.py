"""Contrato JSON de consulta entre playlists y catálogo."""
from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field

BATCH_PATH = "/internal/catalog/songs/batch"
BATCH_LIMIT = 500


@dataclass(frozen=True)
class SongSummary:
    id: UUID
    title: str
    artist_id: UUID
    artist: str
    album: str | None
    duration: float
    cover_url: str | None
    source: str
    license: str
    license_url: str | None
    jamendo_url: str | None
    genres: tuple[str, ...]
    status: str
    available: bool


class SongBatchRequest(BaseModel):
    ids: list[UUID] = Field(max_length=BATCH_LIMIT)


class SongBatchResponse(BaseModel):
    songs: list[SongSummary]
