"""Expenses and scheduled payments

Revision ID: 0004_expenses_payments
Revises: 0003_field
"""
from alembic import op
import sqlalchemy as sa
revision="0004_expenses_payments"
down_revision="0003_field"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("expenses",
      sa.Column("id",sa.String(36),primary_key=True),
      sa.Column("project_id",sa.String(36),sa.ForeignKey("projects.id"),nullable=False),
      sa.Column("description",sa.String(300),nullable=False),
      sa.Column("supplier",sa.String(200),nullable=False),
      sa.Column("amount",sa.Numeric(16,2),nullable=False),
      sa.Column("category",sa.String(20),nullable=False),
      sa.Column("evidence_key",sa.String(500),nullable=True),
      sa.Column("status",sa.String(20),nullable=False),
      sa.Column("created_by",sa.String(200),nullable=False))
    op.create_index("ix_expenses_project_id","expenses",["project_id"])
    op.create_table("payments",
      sa.Column("id",sa.String(36),primary_key=True),
      sa.Column("expense_id",sa.String(36),sa.ForeignKey("expenses.id"),nullable=False),
      sa.Column("amount",sa.Numeric(16,2),nullable=False),
      sa.Column("scheduled_date",sa.Date(),nullable=False),
      sa.Column("status",sa.String(20),nullable=False),
      sa.Column("reference",sa.String(200),nullable=True),
      sa.Column("created_by",sa.String(200),nullable=False),
      sa.Column("confirmed_by",sa.String(200),nullable=True))
    op.create_index("ix_payments_expense_id","payments",["expense_id"])

def downgrade():
    op.drop_index("ix_payments_expense_id",table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_expenses_project_id",table_name="expenses")
    op.drop_table("expenses")
