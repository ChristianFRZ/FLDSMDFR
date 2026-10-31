import uuid

from pydantic import BaseModel, ConfigDict


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
