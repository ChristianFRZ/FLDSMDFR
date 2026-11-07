from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# Un día completo: cualquier valor mayor es un error del cliente.
MAX_SECONDS = 86400


class PlaybackIn(BaseModel):
    playback_id: UUID
    song_id: UUID
    listened_seconds: int = Field(ge=0, le=MAX_SECONDS)


class ProgressIn(BaseModel):
    listened_seconds: int = Field(ge=0, le=MAX_SECONDS)


@dataclass(frozen=True)
class PlaybackEvent:
    seq: int
    playback_id: UUID
    user_id: UUID
    song_id: UUID
    listened_seconds: int
    started_at: datetime
    is_demo: bool


@dataclass(frozen=True)
class RetentionStats:
    at_10s: int
    at_50: int
    at_100: int
