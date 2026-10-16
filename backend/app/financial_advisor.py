"""Financial advisory: evidence-only, tenant-scoped, strictly read-only.

Never settles payments or rewrites contractual values. Money is Decimal.
"""
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Expense, LaborContract, Membership, Payment, Project
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["finance-agent"])
READ_ROLES = ("OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "FIELD_OPERATOR", "VIEWER")
CENT = Decimal("0.01")


def money(value):
    return str(Decimal(value).quantize(CENT))


def diagnose(contracts, expenses, payments, today: date):
    """Pure rules, no I/O. Inputs are trusted records already scoped by project."""
    findings = []
    def emit(code, severity, project_id, message, action, evidence):
        findings.append({"code": code, "severity": severity, "project_id": project_id,
                         "message": message, "recommended_action": action, "evidence": evidence})
    for c in contracts:
        total, advance, balance = c.total, c.reported_advance, c.reported_balance
        if None in (total, advance, balance):
            emit("CONTRACT_VALUES_MISSING", "info", c.project_id,
                 "Contrato com valores incompletos", "Solicitar conferência da fonte contratual.",
                 {"contract_id": c.id, "source_ref": c.source_ref})
            continue
        computed = total - advance
        if abs(computed - balance) >= CENT:
            emit("CONTRACT_BALANCE_DIVERGENCE", "high", c.project_id,
                 "Saldo declarado difere do total menos adiantamento.",
                 "Conferir documento e comprovantes sem sobrescrever o saldo declarado.",
                 {"contract_id": c.id, "source_ref": c.source_ref,
                  "reported_balance": money(balance), "calculated_balance": money(computed),
                  "difference": money(balance - computed)})
    by_expense = {}
    for p in payments:
        by_expense.setdefault(p.expense_id, []).append(p)
    for e in expenses:
        rows = by_expense.get(e.id, [])
        paid = sum((p.amount for p in rows if p.status == "PAID"), Decimal(0))
        scheduled = sum((p.amount for p in rows if p.status == "SCHEDULED"), Decimal(0))
        if paid > e.amount:
            emit("PAYMENTS_EXCEED_EXPENSE", "high", e.project_id,
                 "Pagamentos registrados excedem a despesa.",
                 "Conferir comprovantes e duplicidades; não realizar baixa automática.",
                 {"expense_id": e.id, "amount": money(e.amount), "paid": money(paid)})
        overdue = [p for p in rows if p.status == "SCHEDULED" and p.scheduled_date < today]
        if overdue:
            emit("SCHEDULED_OVERDUE", "warning", e.project_id,
                 "Há pagamentos programados com data vencida.",
                 "Verificar situação e comprovantes antes de qualquer atualização de status.",
                 {"expense_id": e.id, "count": len(overdue),
                  "scheduled_overdue": money(sum((p.amount for p in overdue), Decimal(0)))})
        if e.amount - paid > 0 and not rows:
            emit("UNSCHEDULED_OBLIGATION", "info", e.project_id,
                 "Despesa em aberto sem pagamento programado.",
                 "Conferir programação financeira e documentos.",
                 {"expense_id": e.id, "outstanding": money(e.amount - paid)})
    rank = {"high": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: (rank[f["severity"]], f["code"], f["project_id"],
                                 f["evidence"].get("contract_id", f["evidence"].get("expense_id", ""))))
    return findings


@router.get("/finance-agent/diagnosis")
def financial_diagnosis(subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    """No commit, flush, update, or external call. Isolation enforced in each query."""
    ids = list(db.scalars(select(Project.id).join(
        Membership, Membership.organization_id == Project.organization_id).where(
        Membership.subject_id == subject, Membership.role.in_(READ_ROLES))).all())
    if not ids:
        return {"agent": "financeiro-ia", "version": "1.0", "mode": "advisory",
                "projects": 0, "findings": [], "writes_performed": False}
    contracts = db.scalars(select(LaborContract).where(LaborContract.project_id.in_(ids))).all()
    expenses = db.scalars(select(Expense).where(Expense.project_id.in_(ids))).all()
    expense_ids = [e.id for e in expenses]
    payments = db.scalars(select(Payment).where(Payment.expense_id.in_(expense_ids))).all() if expense_ids else []
    return {"agent": "financeiro-ia", "version": "1.0", "mode": "advisory",
            "projects": len(ids), "findings": diagnose(contracts, expenses, payments, date.today()),
            "writes_performed": False}
