"""playlist covers

Revision ID: 0006_playlist_covers
Revises: 0005_song_covers
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_playlist_covers"
down_revision = "0005_song_covers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("playlists", sa.Column("cover_path", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("playlists", "cover_path")
