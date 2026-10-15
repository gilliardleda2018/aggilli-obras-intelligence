"""Measurement date, notes and review trail (approve/reject with reason).

Revision ID: 0006_measurement_review
Revises: 0005_portfolio_details
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_measurement_review"
down_revision = "0005_portfolio_details"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("measurements") as batch:
        batch.add_column(sa.Column("measured_on", sa.Date(), nullable=True))
        batch.add_column(sa.Column("notes", sa.String(500), nullable=True))
        batch.add_column(sa.Column("decided_by", sa.String(200), nullable=True))
        batch.add_column(sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("decision_reason", sa.String(500), nullable=True))
        batch.create_check_constraint("ck_measurements_status", "status IN ('PENDING','APPROVED','REJECTED')")
        batch.create_check_constraint("ck_measurements_quantity", "quantity > 0")


def downgrade():
    with op.batch_alter_table("measurements") as batch:
        batch.drop_constraint("ck_measurements_quantity", type_="check")
        batch.drop_constraint("ck_measurements_status", type_="check")
        for column in ("decision_reason", "decided_at", "decided_by", "notes", "measured_on"):
            batch.drop_column(column)
