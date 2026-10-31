import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints


class PlaylistIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]


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
