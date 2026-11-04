"""eventos de reproducción con copia de la canción (rama 04: historial degradado)

Revision ID: 0012_playback_snapshots
Revises: 0009_playback_user_index
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_playback_snapshots"
down_revision = "0009_playback_user_index"
branch_labels = None
depends_on = None

# Opcionales: los eventos viejos no tienen copia y una migración no puede preguntarle al
# catálogo. Se completan la próxima vez que el historial se lee con el catálogo arriba.
_COLUMNS = [
    ("title_snapshot", sa.String(200)),
    ("artist_snapshot", sa.String(200)),
    ("album_snapshot", sa.String(200)),
    ("duration_snapshot", sa.Integer()),
]


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        op.add_column("playback_events", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(_COLUMNS):
        op.drop_column("playback_events", name)
