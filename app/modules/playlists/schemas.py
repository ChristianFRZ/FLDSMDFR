import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints


class PlaylistIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]


Role = Literal["owner", "collaborator"]


class MemberOut(BaseModel):
    user_id: uuid.UUID
    name: str


class PlaylistSummary(BaseModel):
    id: uuid.UUID
    name: str
    song_count: int
    updated_at: datetime
    has_cover: bool = False
    role: Role = "owner"


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
    has_cover: bool = False
    role: Role = "owner"
    members: list[MemberOut] = []


class AddSongIn(BaseModel):
    song_id: uuid.UUID


class ReorderIn(BaseModel):
    song_ids: list[uuid.UUID]


class InviteOut(BaseModel):
    token: str
    url: str


class ClaimOut(BaseModel):
    playlist_id: uuid.UUID
    playlist_name: str
    status: Literal["pending", "accepted", "ignored", "member"]


class PendingInviteOut(BaseModel):
    token: str
    playlist_id: uuid.UUID
    playlist_name: str
    invited_by: uuid.UUID
    claimed_at: datetime
