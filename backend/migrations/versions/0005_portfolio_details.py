"""Project details, labor contracts and source traceability.

Revision ID: 0005_portfolio_details
Revises: 0004_expenses_payments

- projects: municipality, address, status, responsible, cost center, coordinates (Marco 06) and source;
  budget/start/end become optional because imported works may not have them yet (never invented).
- expenses: date, notes, contract link and source reference (unique per project) for idempotent imports.
- labor_contracts: contract totals and the advance/balance figures as reported by the source spreadsheet.
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_portfolio_details"
down_revision = "0004_expenses_payments"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("municipality", sa.String(120), nullable=True))
        batch.add_column(sa.Column("address", sa.String(300), nullable=True))
        batch.add_column(sa.Column("status", sa.String(20), nullable=False, server_default="IN_PROGRESS"))
        batch.add_column(sa.Column("responsible", sa.String(200), nullable=True))
        batch.add_column(sa.Column("cost_center", sa.String(60), nullable=True))
        batch.add_column(sa.Column("latitude", sa.Numeric(9, 6), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Numeric(9, 6), nullable=True))
        batch.add_column(sa.Column("source", sa.String(120), nullable=True))
        batch.alter_column("budget", existing_type=sa.Numeric(16, 2), nullable=True)
        batch.alter_column("start_date", existing_type=sa.Date(), nullable=True)
        batch.alter_column("end_date", existing_type=sa.Date(), nullable=True)
        batch.create_check_constraint("ck_projects_status",
                                      "status IN ('PLANNED','IN_PROGRESS','PAUSED','DONE','COST_POOL')")
    op.create_table("labor_contracts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("contractor", sa.String(200), nullable=False),
        sa.Column("description", sa.String(300), nullable=True),
        sa.Column("total", sa.Numeric(16, 2), nullable=True),
        sa.Column("reported_advance", sa.Numeric(16, 2), nullable=True),
        sa.Column("reported_balance", sa.Numeric(16, 2), nullable=True),
        sa.Column("source_ref", sa.String(120), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.UniqueConstraint("project_id", "source_ref", name="uq_labor_contracts_source"))
    op.create_index("ix_labor_contracts_project_id", "labor_contracts", ["project_id"])
    with op.batch_alter_table("expenses") as batch:
        batch.add_column(sa.Column("expense_date", sa.Date(), nullable=True))
        batch.add_column(sa.Column("notes", sa.String(500), nullable=True))
        batch.add_column(sa.Column("contract_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("source_ref", sa.String(120), nullable=True))
        batch.create_foreign_key("fk_expenses_contract", "labor_contracts", ["contract_id"], ["id"])
        batch.create_unique_constraint("uq_expenses_source", ["project_id", "source_ref"])


def downgrade():
    with op.batch_alter_table("expenses") as batch:
        batch.drop_constraint("uq_expenses_source", type_="unique")
        batch.drop_constraint("fk_expenses_contract", type_="foreignkey")
        for column in ("source_ref", "contract_id", "notes", "expense_date"):
            batch.drop_column(column)
    op.drop_index("ix_labor_contracts_project_id", table_name="labor_contracts")
    op.drop_table("labor_contracts")
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT COUNT(*) FROM projects WHERE budget IS NULL OR start_date IS NULL OR end_date IS NULL")).scalar():
        raise RuntimeError("Cannot downgrade: projects without budget or dates exist")
    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("ck_projects_status", type_="check")
        batch.alter_column("end_date", existing_type=sa.Date(), nullable=False)
        batch.alter_column("start_date", existing_type=sa.Date(), nullable=False)
        batch.alter_column("budget", existing_type=sa.Numeric(16, 2), nullable=False)
        for column in ("source", "longitude", "latitude", "cost_center", "responsible", "status", "address", "municipality"):
            batch.drop_column(column)
