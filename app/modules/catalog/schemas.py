import uuid

from pydantic import BaseModel, ConfigDict, Field


class SongOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    artist: str
    album: str
    duration_seconds: int
    is_active: bool


class SongPage(BaseModel):
    items: list[SongOut]
    total: int


class SongUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    artist: str | None = Field(None, min_length=1, max_length=200)
    album: str | None = Field(None, min_length=1, max_length=200)
