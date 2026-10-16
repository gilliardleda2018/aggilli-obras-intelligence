"""Authenticated read-only reconciliation of FOPAG contracts for a project.

No Stripe integration or write operations. Finance scheduling/confirmation remain
the existing operations endpoints and require separate evidence.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import LaborContract, Expense, Payment
from .measurements import access
from .security import require_identity
from .fopag_reconciliation import reconcile_contracts

router = APIRouter(prefix="/api/v1", tags=["fopag-finance"])


@router.get("/projects/{project_id}/fopag/reconciliation")
def project_fopag_reconciliation(project_id: str, subject: str = Depends(require_identity),
                                 db: Session = Depends(get_db)):
    access(db, subject, project_id, ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "VIEWER"])
    rows = db.scalars(select(LaborContract).where(LaborContract.project_id == project_id)
                      .order_by(LaborContract.source_ref, LaborContract.id)).all()
    return reconcile_contracts([
        {"name": c.contractor, "project": project_id, "total": c.total,
         "advance": c.reported_advance, "balance": c.reported_balance}
        for c in rows
    ])


@router.get("/projects/{project_id}/finance/closing-preview")
def closing_preview(project_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    """Read-only settlement summary from persisted expenses and payments."""
    from decimal import Decimal
    from .financial_closing_rules import calculate_settlement
    access(db, subject, project_id, ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "VIEWER"])
    rows = []
    for expense in db.scalars(select(Expense).where(Expense.project_id == project_id)).all():
        payments = db.scalars(select(Payment).where(Payment.expense_id == expense.id)).all()
        paid = tuple(str(p.amount) for p in payments if p.status == "PAID")
        scheduled = sum((p.amount for p in payments if p.status == "SCHEDULED"), Decimal("0"))
        settlement = calculate_settlement(gross=str(expense.amount), payments=paid)
        rows.append({"expense_id": expense.id, "gross": str(settlement.gross),
                     "paid": str(settlement.paid), "scheduled": str(scheduled),
                     "remaining": str(settlement.remaining)})
    return {"rows": rows, "closed": False, "money_moved": False}
