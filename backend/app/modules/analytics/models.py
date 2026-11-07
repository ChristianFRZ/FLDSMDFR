import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AggCursor(Base):
    __tablename__ = "agg_cursor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_seq: Mapped[int] = mapped_column(BigInteger, default=0)


class PlaysHourly(Base):
    __tablename__ = "agg_plays_hourly"

    hour: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    song_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    artist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    genre: Mapped[str] = mapped_column(String(60), index=True)
    plays: Mapped[int] = mapped_column(BigInteger, default=0)


class UserPlays(Base):
    __tablename__ = "agg_user_plays"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    song_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    artist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    genre: Mapped[str] = mapped_column(String(60))
    plays: Mapped[int] = mapped_column(BigInteger, default=0)


class RequestMetric(Base):
    __tablename__ = "request_metrics"

    minute: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    module: Mapped[str] = mapped_column(String(20), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    p50_ms: Mapped[float] = mapped_column(Float, default=0)
    p95_ms: Mapped[float] = mapped_column(Float, default=0)
