"""Field documents (receipts, invoices, quotes) read by OCR and confirmed by a person before becoming expenses.

Revision ID: 0013_field_documents
Revises: 0012_field_photos
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_field_documents"
down_revision = "0012_field_photos"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "field_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", name="fk_field_documents_project"), nullable=True, index=True),
        sa.Column("suggested_project_id", sa.String(36), sa.ForeignKey("projects.id", name="fk_field_documents_suggested"), nullable=True),
        sa.Column("suggestion_reason", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("kind", sa.String(20), nullable=True),
        sa.Column("storage_key", sa.String(80), nullable=False),
        sa.Column("content_type", sa.String(30), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("width", sa.Integer, nullable=False),
        sa.Column("height", sa.Integer, nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("accuracy_m", sa.Numeric(8, 1), nullable=True),
        sa.Column("location_source", sa.String(10), nullable=True),
        sa.Column("access_key", sa.String(44), nullable=True, index=True),
        sa.Column("extraction", sa.String, nullable=True),
        sa.Column("extraction_engine", sa.String(60), nullable=True),
        sa.Column("extraction_error", sa.String(300), nullable=True),
        sa.Column("expense_id", sa.String(36), sa.ForeignKey("expenses.id", name="fk_field_documents_expense"), nullable=True),
        sa.Column("recorded_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_by", sa.String(200), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "sha256", name="uq_field_documents_file"),
        sa.CheckConstraint("status IN ('PENDING','CONFIRMED','DISCARDED')", name="ck_field_documents_status"),
        sa.CheckConstraint("location_source IN ('EXIF','DEVICE')", name="ck_field_documents_location_source"),
    )


def downgrade():
    op.drop_table("field_documents")
