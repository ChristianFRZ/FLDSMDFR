"""catalog: canciones y portadas (equivale a 0002 y 0005 del monolito)

Revision ID: 0001_catalog
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_catalog"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "songs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("artist", sa.String(200), nullable=False),
        sa.Column("album", sa.String(200), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(50), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("cover_path", sa.String(), nullable=True),
    )
    op.create_index("ix_songs_lower_title", "songs", [sa.text("lower(title)")])
    op.create_index("ix_songs_lower_artist", "songs", [sa.text("lower(artist)")])
    op.create_index(
        "ix_songs_lower_artist_created", "songs", [sa.text("lower(artist)"), "created_at"]
    )


def downgrade() -> None:
    op.drop_table("songs")
