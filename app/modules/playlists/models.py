import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Sin FK: users es de otro modulo.
    owner_id: Mapped[uuid.UUID] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cover_path: Mapped[str | None] = mapped_column(String, nullable=True)


class PlaylistSong(Base):
    __tablename__ = "playlist_songs"
    __table_args__ = (
        # Respaldo ante carreras; diferido para que reordenar/recompactar no falle a mitad.
        UniqueConstraint(
            "playlist_id",
            "position",
            name="uq_playlist_songs_position",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    playlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True
    )
    # Sin FK: songs es de otro modulo; los snapshots permiten el modo degradado.
    song_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
    title_snapshot: Mapped[str] = mapped_column(String(200))
    artist_snapshot: Mapped[str] = mapped_column(String(200))
    album_snapshot: Mapped[str] = mapped_column(String(200))
    duration_snapshot: Mapped[int] = mapped_column(Integer)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlaylistMember(Base):
    __tablename__ = "playlist_members"

    playlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True
    )
    # Sin FK: users es de otro modulo.
    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlaylistInvite(Base):
    __tablename__ = "playlist_invites"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    playlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("playlists.id", ondelete="CASCADE"), index=True
    )
    # Sin FK: users es de otro modulo.
    created_by: Mapped[uuid.UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlaylistInviteClaim(Base):
    __tablename__ = "playlist_invite_claims"

    token: Mapped[str] = mapped_column(
        ForeignKey("playlist_invites.token", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, index=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "accepted", "ignored", name="invite_status")
    )
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
