import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.catalog.schemas import SongOut


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
    total_songs: int
    total_users: int
    top: list[TopSongOut]


class HistoryItemOut(BaseModel):
    song: SongOut
    last_played_at: datetime
    available: bool


class HistoryPage(BaseModel):
    items: list[HistoryItemOut]
    total: int


class TopArtistOut(BaseModel):
    artist: str
    play_count: int
    song_count: int
    cover_song_id: uuid.UUID | None
