"""playback user index

Revision ID: 0009_playback_user_index
Revises: 0008_playlist_invites
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_playback_user_index"
down_revision = "0008_playlist_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_playback_events_user_occurred",
        "playback_events",
        ["user_id", sa.text("occurred_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_playback_events_user_occurred", table_name="playback_events")
