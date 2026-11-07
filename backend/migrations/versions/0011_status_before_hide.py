"""estado de una pista antes de que un administrador la oculte"""
from alembic import op
import sqlalchemy as sa


revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('songs', sa.Column('status_before_hide', sa.String(length=20), nullable=True))


def downgrade():
    op.drop_column('songs', 'status_before_hide')
