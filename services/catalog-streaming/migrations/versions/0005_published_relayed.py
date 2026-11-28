"""marca de relevo del outbox de track_published"""
from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('published_events', sa.Column('relayed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('published_events', 'relayed_at')
