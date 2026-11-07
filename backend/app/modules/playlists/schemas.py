from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlaylistIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_public: bool = False


class PlaylistPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_public: bool | None = None


class AddSongIn(BaseModel):
    song_id: UUID


class PlaylistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    is_public: bool
    created_at: datetime
