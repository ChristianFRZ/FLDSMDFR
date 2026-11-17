"""Esquema inicial de playbacks."""
from importlib import import_module

revision = "playbacks_01"
down_revision = branch_labels = depends_on = None

REVISIONS = ['0007_playback', '0010_analytics']


def upgrade():
    for name in REVISIONS:
        import_module("migrations.versions." + name).upgrade()


def downgrade():
    for name in reversed(REVISIONS):
        import_module("migrations.versions." + name).downgrade()
