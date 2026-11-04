import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.clients.catalog_schemas import SongOut


class FavoriteSongOut(BaseModel):
    song_id: uuid.UUID
    title: str
    artist: str
    album: str
    duration_seconds: int
    has_cover: bool
    status: Literal["ok", "degraded", "unavailable"]
    added_at: datetime


class FavoritesOut(BaseModel):
    songs: list[FavoriteSongOut]
    total_seconds: int
    degraded: bool = False  # el catálogo no respondió: los datos son las últimas copias


class FollowOut(BaseModel):
    artist: str
    followed_at: datetime
    song_count: int
    cover_song_id: uuid.UUID | None


class InviteNotice(BaseModel):
    token: str
    playlist_id: uuid.UUID
    playlist_name: str
    inviter_name: str


class NotificationOut(BaseModel):
    id: str
    type: Literal["release", "invite"]
    created_at: datetime
    read: bool
    song: SongOut | None = None
    invite: InviteNotice | None = None


class NotificationsOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int


class MarkReadIn(BaseModel):
    ids: list[Annotated[str, StringConstraints(min_length=1, max_length=120)]] = Field(
        max_length=100
    )
