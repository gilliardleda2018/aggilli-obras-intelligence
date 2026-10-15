"""Spreadsheet import batches (preview kept server-side until the user confirms).

Revision ID: 0008_import_batches
Revises: 0007_forecast_runs
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_import_batches"
down_revision = "0007_forecast_runs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("import_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("filename", sa.String(200), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("rows", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('PREVIEW','COMMITTED','DISCARDED')", name="ck_import_batches_status"))
    op.create_index("ix_import_batches_org", "import_batches", ["organization_id", "created_at"])


def downgrade():
    op.drop_index("ix_import_batches_org", table_name="import_batches")
    op.drop_table("import_batches")
