"""playlists

Revision ID: 0003_playlists
Revises: 0001_users
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_playlists"
down_revision = "0001_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "playlists",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_playlists_owner_id", "playlists", ["owner_id"])
    op.create_table(
        "playlist_songs",
        sa.Column(
            "playlist_id",
            sa.Uuid(),
            sa.ForeignKey("playlists.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("song_id", sa.Uuid(), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title_snapshot", sa.String(200), nullable=False),
        sa.Column("artist_snapshot", sa.String(200), nullable=False),
        sa.Column("album_snapshot", sa.String(200), nullable=False),
        sa.Column("duration_snapshot", sa.Integer(), nullable=False),
        sa.Column(
            "added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "playlist_id",
            "position",
            name="uq_playlist_songs_position",
            deferrable=True,
            initially="DEFERRED",
        ),
    )


def downgrade() -> None:
    op.drop_table("playlist_songs")
    op.drop_table("playlists")
