import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Artist(Base):
    __tablename__ = "artists"
    __table_args__ = (Index("ix_artists_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(20), default="local")
    jamendo_id: Mapped[str | None] = mapped_column(String(40), unique=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True)
    bio: Mapped[str] = mapped_column(Text, default="")
    photo_path: Mapped[str | None] = mapped_column(String(200))
    links: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    artist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="album")
    cover_path: Mapped[str | None] = mapped_column(String(200))
    cover_url: Mapped[str | None] = mapped_column(String(500))
    jamendo_id: Mapped[str | None] = mapped_column(String(40), unique=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Song(Base):
    __tablename__ = "songs"
    __table_args__ = (
        Index("ix_songs_title_trgm", "title", postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"}),
        Index("ix_songs_genres", "genres", postgresql_using="gin"),
        Index("ix_songs_status_publish_at", "status", "publish_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300))
    artist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), index=True)
    album_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("albums.id", ondelete="SET NULL"))
    duration: Mapped[float] = mapped_column(Float, default=0)
    genres: Mapped[list[str]] = mapped_column(ARRAY(String(60)), default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(60)), default=list)
    source: Mapped[str] = mapped_column(String(20), default="local", index=True)
    license: Mapped[str] = mapped_column(String(120), default="")
    license_url: Mapped[str | None] = mapped_column(String(300))
    jamendo_id: Mapped[str | None] = mapped_column(String(40), unique=True)
    jamendo_url: Mapped[str | None] = mapped_column(String(300))
    audio_url: Mapped[str | None] = mapped_column(String(600))
    audio_path: Mapped[str | None] = mapped_column(String(200))
    cover_path: Mapped[str | None] = mapped_column(String(200))
    cover_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hidden_reason: Mapped[str | None] = mapped_column(Text)
    hidden_by_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    status_before_hide: Mapped[str | None] = mapped_column(String(20))
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    artist: Mapped[Artist] = relationship(lazy="joined", innerjoin=True)
    album: Mapped[Album | None] = relationship(lazy="joined")


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    genre_index: Mapped[int] = mapped_column(Integer, default=0)
    offset: Mapped[int] = mapped_column(Integer, default=0)
    imported: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublishedEvent(Base):
    """Registro único de track_published."""

    __tablename__ = "published_events"

    song_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
