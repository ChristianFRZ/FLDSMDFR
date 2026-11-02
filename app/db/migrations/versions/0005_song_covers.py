"""song covers

Revision ID: 0005_song_covers
Revises: 0004_playback
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_song_covers"
down_revision = "0004_playback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("songs", sa.Column("cover_path", sa.String(), nullable=True))
    op.create_index(
        "ix_songs_lower_artist_created", "songs", [sa.text("lower(artist)"), "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_songs_lower_artist_created", table_name="songs")
    op.drop_column("songs", "cover_path")
