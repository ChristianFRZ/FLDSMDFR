"""Tipos que viajan entre servicios. Son los mismos que antes devolvían los public.py."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class AuthState(BaseModel):
    id: UUID
    role: str
    status: str


class SongSummary(BaseModel):
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


class ArtistSummary(BaseModel):
    id: UUID
    name: str
    source: str
    bio: str
    photo_url: str | None
    links: dict


class UpcomingRelease(BaseModel):
    song_id: UUID
    title: str
    artist_id: UUID
    artist: str
    publish_at: datetime


class PublishedRelease(BaseModel):
    song: SongSummary
    published_at: datetime


class ReleaseCounts(BaseModel):
    scheduled: int
    published: int


class UserGrowthPoint(BaseModel):
    day: date
    listener: int
    composer: int
    admin: int


class TapeActivity(BaseModel):
    tapes: int
    members: int
    tracks: int
    dedications: int


class AuditEntry(BaseModel):
    actor_id: UUID | None = None
    action: str
    target_type: str
    target_id: str
    detail: dict | None = None
    outcome: str = "ok"
