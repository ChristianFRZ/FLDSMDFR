"""favoritas con copia de la canción (rama 04: modo degradado)

Revision ID: 0011_favorite_snapshots
Revises: 0010_social
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_favorite_snapshots"
down_revision = "0010_social"
branch_labels = None
depends_on = None

# Opcionales: las filas viejas no tienen copia y una migración no puede preguntarle al catálogo.
# Se completan la próxima vez que se leen con el catálogo arriba.
_COLUMNS = [
    ("title_snapshot", sa.String(200)),
    ("artist_snapshot", sa.String(200)),
    ("album_snapshot", sa.String(200)),
    ("duration_snapshot", sa.Integer()),
]


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        op.add_column("favorites", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(_COLUMNS):
        op.drop_column("favorites", name)
