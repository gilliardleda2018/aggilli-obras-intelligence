"""Human review of automatic alerts (confirmed / false alarm), kept to improve the detectors.

Revision ID: 0009_alert_reviews
Revises: 0008_import_batches
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_alert_reviews"
down_revision = "0008_import_batches"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("alert_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("alert_key", sa.String(200), nullable=False),
        sa.Column("alert_type", sa.String(40), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("reviewed_by", sa.String(200), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "alert_key", name="uq_alert_reviews_key"),
        sa.CheckConstraint("decision IN ('CONFIRMED','FALSE_ALARM','RESOLVED')", name="ck_alert_reviews_decision"))


def downgrade():
    op.drop_table("alert_reviews")
