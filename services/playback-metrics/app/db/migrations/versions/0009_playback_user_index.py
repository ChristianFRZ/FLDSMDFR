"""playback user index

Revision ID: 0009_playback_user_index
Revises: 0004_playback
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_playback_user_index"
down_revision = "0004_playback"
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
