"""Work diary photos: original file reference, integrity hash, capture time and location with provenance.

Revision ID: 0012_field_photos
Revises: 0011_project_location
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_field_photos"
down_revision = "0011_project_location"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "field_photos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("report_id", sa.String(36), sa.ForeignKey("field_reports.id", name="fk_field_photos_report"), nullable=True, index=True),
        sa.Column("service_id", sa.String(36), sa.ForeignKey("service_items.id", name="fk_field_photos_service"), nullable=True, index=True),
        sa.Column("caption", sa.String(300), nullable=True),
        sa.Column("storage_key", sa.String(80), nullable=False),
        sa.Column("content_type", sa.String(30), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("width", sa.Integer, nullable=False),
        sa.Column("height", sa.Integer, nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("taken_at_source", sa.String(10), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("accuracy_m", sa.Numeric(8, 1), nullable=True),
        sa.Column("location_source", sa.String(10), nullable=True),
        sa.Column("distance_m", sa.Integer, nullable=True),
        sa.Column("recorded_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "sha256", name="uq_field_photos_file"),
        sa.CheckConstraint("location_source IN ('EXIF','DEVICE')", name="ck_field_photos_location_source"),
        sa.CheckConstraint("taken_at_source IN ('EXIF','DEVICE')", name="ck_field_photos_taken_at_source"),
    )


def downgrade():
    op.drop_table("field_photos")
