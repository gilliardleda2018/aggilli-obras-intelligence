"""Materials: category, minimum stock, planned consumption and service link; movements with date, cost and origin.

Revision ID: 0010_materials_stock
Revises: 0009_alert_reviews
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_materials_stock"
down_revision = "0009_alert_reviews"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("materials") as batch:
        batch.add_column(sa.Column("category", sa.String(60), nullable=True))
        batch.add_column(sa.Column("min_stock", sa.Numeric(16, 3), nullable=True))
        batch.add_column(sa.Column("planned_quantity", sa.Numeric(16, 3), nullable=True))
        batch.add_column(sa.Column("service_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_materials_service", "service_items", ["service_id"], ["id"])
    with op.batch_alter_table("stock_movements") as batch:
        batch.add_column(sa.Column("movement_date", sa.Date(), nullable=True))
        batch.add_column(sa.Column("unit_cost", sa.Numeric(16, 4), nullable=True))
        batch.add_column(sa.Column("supplier", sa.String(200), nullable=True))
        batch.add_column(sa.Column("note", sa.String(300), nullable=True))
        batch.add_column(sa.Column("expense_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_stock_movements_expense", "expenses", ["expense_id"], ["id"])
        batch.create_check_constraint("ck_stock_movements_kind", "kind IN ('IN','OUT')")
        batch.create_check_constraint("ck_stock_movements_quantity", "quantity > 0")


def downgrade():
    with op.batch_alter_table("stock_movements") as batch:
        batch.drop_constraint("ck_stock_movements_quantity", type_="check")
        batch.drop_constraint("ck_stock_movements_kind", type_="check")
        batch.drop_constraint("fk_stock_movements_expense", type_="foreignkey")
        for column in ("expense_id", "note", "supplier", "unit_cost", "movement_date"):
            batch.drop_column(column)
    with op.batch_alter_table("materials") as batch:
        batch.drop_constraint("fk_materials_service", type_="foreignkey")
        for column in ("service_id", "planned_quantity", "min_stock", "category"):
            batch.drop_column(column)
