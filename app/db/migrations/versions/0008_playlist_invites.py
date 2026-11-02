"""playlist invites

Revision ID: 0008_playlist_invites
Revises: 0007_playlist_members
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_playlist_invites"
down_revision = "0007_playlist_members"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "playlist_invites",
        sa.Column("token", sa.String(64), primary_key=True),
        sa.Column(
            "playlist_id",
            sa.Uuid(),
            sa.ForeignKey("playlists.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "playlist_invite_claims",
        sa.Column(
            "token",
            sa.String(64),
            sa.ForeignKey("playlist_invites.token", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("user_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "status",
            sa.Enum("pending", "accepted", "ignored", name="invite_status"),
            nullable=False,
        ),
        sa.Column(
            "claimed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_playlist_invite_claims_user_id", "playlist_invite_claims", ["user_id"])


def downgrade() -> None:
    op.drop_table("playlist_invite_claims")
    op.drop_table("playlist_invites")
    sa.Enum(name="invite_status").drop(op.get_bind(), checkfirst=True)
