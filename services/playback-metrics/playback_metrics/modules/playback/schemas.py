from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


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
