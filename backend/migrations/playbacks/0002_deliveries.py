"""Acuses para entregas repetidas de un evento."""
from alembic import op
import sqlalchemy as sa

revision = "playbacks_02"
down_revision = "playbacks_01"
branch_labels = depends_on = None


def upgrade():
    op.create_table("playback_deliveries", sa.Column("id", sa.Uuid(), primary_key=True))


def downgrade():
    op.drop_table("playback_deliveries")
