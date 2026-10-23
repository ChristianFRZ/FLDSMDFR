from core.module_catalog.models import SongResponse
from pydantic import BaseModel, Field


class PlaylistCreate(BaseModel):
    user_id: int
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class PlaylistAddSong(BaseModel):
    song_id: int


class PlaylistResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None
    created_at: str


class PlaylistDetailResponse(PlaylistResponse):
    songs: list[SongResponse]
