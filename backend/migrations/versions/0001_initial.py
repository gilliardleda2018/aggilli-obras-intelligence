"""Initial multi-tenant project schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
from app.db import Base
from app import models  # noqa: F401
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    tables = [Base.metadata.tables[name] for name in (
        "organizations", "memberships", "projects", "service_items",
        "measurements", "audit_events")]
    Base.metadata.create_all(bind=op.get_bind(), tables=tables)

def downgrade():
    tables = [Base.metadata.tables[name] for name in (
        "organizations", "memberships", "projects", "service_items",
        "measurements", "audit_events")]
    Base.metadata.drop_all(bind=op.get_bind(), tables=tables)
