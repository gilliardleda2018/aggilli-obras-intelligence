"""Materials and costs

Revision ID: 0002_stock_costs
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa
revision = "0002_stock_costs"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("materials",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id"),nullable=False),
        sa.Column("name",sa.String(200),nullable=False),
        sa.Column("unit",sa.String(30),nullable=False))
    op.create_index("ix_materials_project_id","materials",["project_id"])
    op.create_table("stock_movements",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("material_id",sa.String(36),sa.ForeignKey("materials.id"),nullable=False),
        sa.Column("kind",sa.String(3),nullable=False),
        sa.Column("quantity",sa.Numeric(16,3),nullable=False),
        sa.Column("recorded_by",sa.String(200),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_stock_movements_material_id","stock_movements",["material_id"])
    op.create_table("cost_entries",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id"),nullable=False),
        sa.Column("description",sa.String(300),nullable=False),
        sa.Column("amount",sa.Numeric(16,2),nullable=False),
        sa.Column("recorded_by",sa.String(200),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_cost_entries_project_id","cost_entries",["project_id"])

def downgrade():
    op.drop_index("ix_cost_entries_project_id",table_name="cost_entries")
    op.drop_table("cost_entries")
    op.drop_index("ix_stock_movements_material_id",table_name="stock_movements")
    op.drop_table("stock_movements")
    op.drop_index("ix_materials_project_id",table_name="materials")
    op.drop_table("materials")
