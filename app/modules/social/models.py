import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Sin FK: users y songs son de otros modulos; las referencias son identificadores.


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    song_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ArtistFollow(Base):
    __tablename__ = "artist_follows"

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    artist_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    artist_name: Mapped[str] = mapped_column(String(200))
    followed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NotificationRead(Base):
    __tablename__ = "notification_reads"

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    notification_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
