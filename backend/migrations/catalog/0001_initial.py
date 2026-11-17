"""Esquema inicial de catalog."""
from importlib import import_module

revision = "catalog_01"
down_revision = branch_labels = depends_on = None

REVISIONS = ['0003_catalog', '0004_catalog_jobs', '0005_catalog_publishing', '0011_status_before_hide', '0012_catalog_audit']


def upgrade():
    for name in REVISIONS:
        import_module("migrations.versions." + name).upgrade()


def downgrade():
    for name in reversed(REVISIONS):
        import_module("migrations.versions." + name).downgrade()
