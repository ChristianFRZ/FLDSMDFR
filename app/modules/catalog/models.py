import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Song(Base):
    __tablename__ = "songs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    artist: Mapped[str] = mapped_column(String(200))
    album: Mapped[str] = mapped_column(String(200))
    duration_seconds: Mapped[int]
    file_path: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String(50))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cover_path: Mapped[str | None] = mapped_column(String, nullable=True)

    @property
    def has_cover(self) -> bool:
        return self.cover_path is not None


Index("ix_songs_lower_title", func.lower(Song.title))
Index("ix_songs_lower_artist", func.lower(Song.artist))
Index("ix_songs_lower_artist_created", func.lower(Song.artist), Song.created_at)
