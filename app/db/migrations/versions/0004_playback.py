"""playback

Revision ID: 0004_playback
Revises: 0003_playlists
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_playback"
down_revision = "0003_playlists"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "playback_events",
        sa.Column("playback_id", sa.Uuid(), primary_key=True),
        sa.Column("song_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("listened_seconds", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_playback_events_song_id", "playback_events", ["song_id"])
    op.create_table(
        "song_play_counts",
        sa.Column("song_id", sa.Uuid(), primary_key=True),
        sa.Column("play_count", sa.BigInteger(), nullable=False),
        sa.Column("last_played_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("song_play_counts")
    op.drop_table("playback_events")
