"""Forecast history: every recalculation is kept with model, version and the hash of its inputs.

Revision ID: 0007_forecast_runs
Revises: 0006_measurement_review
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_forecast_runs"
down_revision = "0006_measurement_review"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("forecast_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("model", sa.String(60), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "kind", "model", "version", "input_hash", name="uq_forecast_runs_inputs"))
    op.create_index("ix_forecast_runs_project", "forecast_runs", ["project_id", "kind", "created_at"])


def downgrade():
    op.drop_index("ix_forecast_runs_project", table_name="forecast_runs")
    op.drop_table("forecast_runs")
