"""Entrega recuperable de la auditoría del catálogo."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0012"
down_revision = "0011"
branch_labels = depends_on = None


def upgrade():
    op.create_table("catalog_pending_audit", sa.Column("id", sa.Uuid(), primary_key=True),
                    sa.Column("payload", JSONB, nullable=False))


def downgrade():
    op.drop_table("catalog_pending_audit")
