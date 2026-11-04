import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.clients.catalog_schemas import SongOut


class PlaybackIn(BaseModel):
    playback_id: uuid.UUID
    song_id: uuid.UUID
    listened_seconds: int = Field(ge=10, le=86400)
    occurred_at: datetime | None = None


class PlaybackOut(BaseModel):
    playback_id: uuid.UUID
    counted: bool


class TopSongOut(BaseModel):
    song_id: uuid.UUID
    title: str
    artist: str
    album: str
    play_count: int
    # Canción completa para reproducir desde el top; None si el catálogo no respondió.
    song: SongOut | None = None


class MetricsSummary(BaseModel):
    total_playbacks: int
    total_songs: int | None  # None: catalog-streaming no respondió
    total_users: int | None  # None: users-playlists no respondió
    top: list[TopSongOut]
    degraded: bool = False


class HistoryItemOut(BaseModel):
    song: SongOut
    last_played_at: datetime
    available: bool  # compatibilidad: True solo con status == "ok"
    status: Literal["ok", "degraded", "unavailable"]


class HistoryPage(BaseModel):
    items: list[HistoryItemOut]
    total: int
    degraded: bool = False  # el catálogo no respondió: los datos son las últimas copias


class TopArtistOut(BaseModel):
    artist: str
    play_count: int
    song_count: int
    cover_song_id: uuid.UUID | None
