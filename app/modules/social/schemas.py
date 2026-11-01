import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class FavoriteSongOut(BaseModel):
    song_id: uuid.UUID
    title: str
    artist: str
    album: str
    duration_seconds: int
    has_cover: bool
    status: Literal["ok", "unavailable"]
    added_at: datetime


class FavoritesOut(BaseModel):
    songs: list[FavoriteSongOut]
    total_seconds: int


class FollowOut(BaseModel):
    artist: str
    followed_at: datetime
    song_count: int
    cover_song_id: uuid.UUID | None
