"""Field reports and inspections.

Revision ID: 0003_field
Revises: 0002_stock_costs
"""
from alembic import op
import sqlalchemy as sa
revision = "0003_field"
down_revision = "0002_stock_costs"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("field_reports",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id"),nullable=False),
        sa.Column("report_date",sa.Date(),nullable=False),
        sa.Column("weather",sa.String(100),nullable=False),
        sa.Column("summary",sa.String(5000),nullable=False),
        sa.Column("recorded_by",sa.String(200),nullable=False))
    op.create_index("ix_field_reports_project_id","field_reports",["project_id"])
    op.create_table("inspections",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id"),nullable=False),
        sa.Column("description",sa.String(2000),nullable=False),
        sa.Column("status",sa.String(20),nullable=False),
        sa.Column("recorded_by",sa.String(200),nullable=False))
    op.create_index("ix_inspections_project_id","inspections",["project_id"])

def downgrade():
    op.drop_index("ix_inspections_project_id",table_name="inspections")
    op.drop_table("inspections")
    op.drop_index("ix_field_reports_project_id",table_name="field_reports")
    op.drop_table("field_reports")
