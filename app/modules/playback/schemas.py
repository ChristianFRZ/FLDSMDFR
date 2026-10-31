import uuid
from datetime import datetime

from pydantic import BaseModel, Field


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


class MetricsSummary(BaseModel):
    total_playbacks: int
    total_songs: int
    total_users: int
    top: list[TopSongOut]
