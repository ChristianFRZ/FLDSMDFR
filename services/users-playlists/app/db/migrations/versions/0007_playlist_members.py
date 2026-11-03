"""playlist members

Revision ID: 0007_playlist_members
Revises: 0006_playlist_covers
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_playlist_members"
down_revision = "0006_playlist_covers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "playlist_members",
        sa.Column(
            "playlist_id",
            sa.Uuid(),
            sa.ForeignKey("playlists.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("user_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_playlist_members_user_id", "playlist_members", ["user_id"])


def downgrade() -> None:
    op.drop_table("playlist_members")
