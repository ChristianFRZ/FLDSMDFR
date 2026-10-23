from pydantic import BaseModel, Field


class SongBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    artist: str = Field(..., min_length=1, max_length=100)
    album: str = Field(default="Single", max_length=150)
    duration_seconds: int = Field(..., gt=0)
    mime_type: str = Field(default="audio/wav")


class SongCreate(SongBase):
    file_path: str = Field(..., min_length=1)


class SongResponse(SongBase):
    id: int
    file_path: str
    created_at: str
