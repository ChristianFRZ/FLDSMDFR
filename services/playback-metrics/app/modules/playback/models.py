import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlaybackEvent(Base):
    """Evento de reproduccion; `playback_id` (generado por el cliente) da la idempotencia."""

    __tablename__ = "playback_events"

    playback_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    # Sin FK: songs y users son de otros modulos.
    song_id: Mapped[uuid.UUID] = mapped_column(index=True)
    user_id: Mapped[uuid.UUID]
    listened_seconds: Mapped[int] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


Index(
    "ix_playback_events_user_occurred",
    PlaybackEvent.user_id,
    PlaybackEvent.occurred_at.desc(),
)


class SongPlayCount(Base):
    __tablename__ = "song_play_counts"

    song_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    play_count: Mapped[int] = mapped_column(BigInteger, default=0)
    last_played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
