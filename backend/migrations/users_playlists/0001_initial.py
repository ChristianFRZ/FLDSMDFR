"""Esquema inicial de users_playlists."""
from importlib import import_module

revision = "users_playlists_01"
down_revision = branch_labels = depends_on = None

REVISIONS = ['0001_users', '0002_users_audit', '0006_playlists', '0008_social', '0009_tapes']


def upgrade():
    for name in REVISIONS:
        import_module("migrations.versions." + name).upgrade()


def downgrade():
    for name in reversed(REVISIONS):
        import_module("migrations.versions." + name).downgrade()
