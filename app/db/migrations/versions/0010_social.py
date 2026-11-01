"""social

Revision ID: 0010_social
Revises: 0009_playback_user_index
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_social"
down_revision = "0009_playback_user_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    now = sa.func.now()
    op.create_table(
        "favorites",
        sa.Column("user_id", sa.Uuid(), primary_key=True),
        sa.Column("song_id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
    )
    op.create_table(
        "artist_follows",
        sa.Column("user_id", sa.Uuid(), primary_key=True),
        sa.Column("artist_key", sa.String(200), primary_key=True),
        sa.Column("artist_name", sa.String(200), nullable=False),
        sa.Column("followed_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
    )
    op.create_table(
        "notification_reads",
        sa.Column("user_id", sa.Uuid(), primary_key=True),
        sa.Column("notification_id", sa.String(120), primary_key=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
    )


def downgrade() -> None:
    op.drop_table("notification_reads")
    op.drop_table("artist_follows")
    op.drop_table("favorites")
