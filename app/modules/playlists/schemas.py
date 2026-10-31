import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PlaylistIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class PlaylistSummary(BaseModel):
    id: uuid.UUID
    name: str
    song_count: int
    updated_at: datetime


class PlaylistSongOut(BaseModel):
    song_id: uuid.UUID
    title: str
    artist: str
    album: str
    duration_seconds: int
    position: int
    status: Literal["ok", "degraded", "unavailable"]


class PlaylistDetail(BaseModel):
    id: uuid.UUID
    name: str
    songs: list[PlaylistSongOut]
    total_seconds: int


class AddSongIn(BaseModel):
    song_id: uuid.UUID


class ReorderIn(BaseModel):
    song_ids: list[uuid.UUID]
