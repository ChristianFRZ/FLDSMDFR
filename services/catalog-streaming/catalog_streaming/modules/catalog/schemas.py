from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


@dataclass(frozen=True)
class ArtistSummary:
    id: UUID
    name: str
    source: str
    bio: str
    photo_url: str | None
    links: dict


@dataclass(frozen=True)
class UpcomingRelease:
    song_id: UUID
    title: str
    artist_id: UUID
    artist: str
    publish_at: datetime


@dataclass(frozen=True)
class PublishedRelease:
    song: SongSummary
    published_at: datetime


@dataclass(frozen=True)
class ReleaseCounts:
    scheduled: int
    published: int


class ImportIn(BaseModel):
    genres: list[str] = Field(default_factory=list, max_length=30)
    limit_per_genre: int = Field(default=200, ge=1, le=5000)
    order: str = "popularity_total"


class ImportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    params: dict
    offset: int
    imported: int
    error: str | None
    created_at: datetime
    finished_at: datetime | None


class TrackPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    genre: str | None = Field(default=None, min_length=1, max_length=60)
    license: str | None = Field(default=None, min_length=1, max_length=120)
    album_id: UUID | None = None
    publish_at: datetime | None = None

    @field_validator("title", "genre", "license")
    @classmethod
    def not_null(cls, value: str | None) -> str:
        """Omitirlo deja el valor como está. Mandarlo en null dejaría la pista sin ese dato."""
        if value is None:
            raise ValueError("No puede quedar vacío")
        return value


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    bio: str = Field(default="", max_length=2000)
    links: dict[str, str] = Field(default_factory=dict)

    @field_validator("links")
    @classmethod
    def only_web_links(cls, links: dict[str, str]) -> dict[str, str]:
        """Se muestran como enlaces en la página pública: un javascript: correría en el navegador de quien lo abra."""
        for url in links.values():
            if not url.lower().startswith(("http://", "https://")):
                raise ValueError("Los enlaces deben empezar con http:// o https://")
        return links


class HideIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
