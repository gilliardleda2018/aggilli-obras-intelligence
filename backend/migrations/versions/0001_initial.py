"""Initial multi-tenant project schema.

Revision ID: 0001_initial
Revises:

The schema is spelled out explicitly (frozen) instead of being derived from the current
models, so later migrations can add columns without colliding with this one.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

INDEXES = {"memberships": "organization_id", "projects": "organization_id", "service_items": "project_id",
           "measurements": "service_item_id", "audit_events": "organization_id"}


def upgrade():
    op.create_table("organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False))
    op.create_table("memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("subject_id", sa.String(200), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.UniqueConstraint("organization_id", "subject_id"))
    op.create_table("projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("location", sa.String(300), nullable=False),
        sa.Column("budget", sa.Numeric(16, 2), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False))
    op.create_table("service_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("planned_quantity", sa.Numeric(16, 3), nullable=False),
        sa.Column("weight", sa.Numeric(7, 4), nullable=False))
    op.create_table("measurements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("service_item_id", sa.String(36), sa.ForeignKey("service_items.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(16, 3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("recorded_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("subject_id", sa.String(200), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for table, column in INDEXES.items():
        op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    for table, column in INDEXES.items():
        op.drop_index(f"ix_{table}_{column}", table_name=table)
    for table in ("audit_events", "measurements", "service_items", "projects", "memberships", "organizations"):
        op.drop_table(table)
