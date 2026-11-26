"""lanzamientos recibidos por el stream track_published"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('release_events',
    sa.Column('song_id', sa.UUID(), nullable=False),
    sa.Column('artist_id', sa.UUID(), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('song', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.PrimaryKeyConstraint('song_id')
    )
    op.create_index('ix_release_events_artist_published', 'release_events', ['artist_id', 'published_at'], unique=False)


def downgrade():
    op.drop_index('ix_release_events_artist_published', table_name='release_events')
    op.drop_table('release_events')
