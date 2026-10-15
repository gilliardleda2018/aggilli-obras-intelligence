"""Portfolio views computed from persisted records: works, weekly payment schedule and labor contracts.

Every figure here comes from the database. Payments are reported by status (scheduled vs paid with
evidence); physical progress only comes from approved measurements and is never derived from money.
"""
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from .db import get_db
from .measurements import access
from .models import (AuditEvent, Expense, FieldReport, LaborContract, Measurement, Membership, Payment, Project,
                     PROJECT_STATUSES, ServiceItem)
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["portfolio"])
READ_ROLES = ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "FIELD_OPERATOR", "VIEWER"]
ZERO = Decimal("0")


def _money(value) -> str:
    return str(Decimal(str(value or 0)).quantize(Decimal("0.01")))


def _authorized_projects(db: Session, subject: str) -> list[Project]:
    return list(db.scalars(select(Project).join(Membership, Membership.organization_id == Project.organization_id)
                           .where(Membership.subject_id == subject, Membership.role.in_(READ_ROLES))
                           .order_by(Project.name)).all())


def _physical(db: Session, project_ids: list[str]) -> dict[str, dict]:
    """Weighted progress from approved measurements; planning_complete when weights add up to 100."""
    approved = (select(Measurement.service_item_id, func.sum(Measurement.quantity).label("qty"))
                .where(Measurement.status == "APPROVED").group_by(Measurement.service_item_id).subquery())
    rows = db.execute(select(ServiceItem.project_id, ServiceItem.weight, ServiceItem.planned_quantity, approved.c.qty)
                      .outerjoin(approved, approved.c.service_item_id == ServiceItem.id)
                      .where(ServiceItem.project_id.in_(project_ids))).all()
    result: dict[str, dict] = {}
    for project_id, weight, planned, qty in rows:
        entry = result.setdefault(project_id, {"weight": ZERO, "done": ZERO, "services": 0})
        fraction = min(Decimal(1), Decimal(str(qty or 0)) / planned) if planned else ZERO
        entry["weight"] += weight
        entry["done"] += weight * fraction
        entry["services"] += 1
    return result


@router.get("/portfolio")
def portfolio(subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    projects = _authorized_projects(db, subject)
    ids = [p.id for p in projects]
    if not ids:
        return {"projects": [], "totals": {}}
    expenses = dict(db.execute(select(Expense.project_id, func.sum(Expense.amount))
                               .where(Expense.project_id.in_(ids)).group_by(Expense.project_id)).all())
    payments = {}
    for project_id, status, amount in db.execute(
            select(Expense.project_id, Payment.status, func.sum(Payment.amount)).join(Expense, Payment.expense_id == Expense.id)
            .where(Expense.project_id.in_(ids)).group_by(Expense.project_id, Payment.status)).all():
        payments.setdefault(project_id, {})[status] = amount
    # advance_valued: advances of contracts that have a total, so the advance ratio never mixes unknown totals.
    valued = case((LaborContract.total.is_not(None), LaborContract.reported_advance), else_=None)
    contracts = {project_id: (total, advance, balance, count, adv_valued) for project_id, total, advance, balance, count, adv_valued
                 in db.execute(select(LaborContract.project_id, func.sum(LaborContract.total), func.sum(LaborContract.reported_advance),
                                      func.sum(LaborContract.reported_balance), func.count(LaborContract.id), func.sum(valued))
                               .where(LaborContract.project_id.in_(ids)).group_by(LaborContract.project_id)).all()}
    physical = _physical(db, ids)
    latest_reports = {}
    for report in db.scalars(select(FieldReport).where(FieldReport.project_id.in_(ids))
                             .order_by(FieldReport.report_date.desc())).all():
        latest_reports.setdefault(report.project_id, report)
    flagged = dict(db.execute(select(Expense.project_id, func.count(Expense.id))
                              .where(Expense.project_id.in_(ids), Expense.notes.is_not(None)).group_by(Expense.project_id)).all())
    rows = []
    for p in projects:
        progress = physical.get(p.id)
        total, advance, balance, count, adv_valued = contracts.get(p.id, (ZERO, ZERO, ZERO, 0, ZERO))
        rows.append({
            "id": p.id, "name": p.name, "location": p.location, "municipality": p.municipality, "status": p.status,
            "responsible": p.responsible, "budget": None if p.budget is None else _money(p.budget),
            "latitude": None if p.latitude is None else float(p.latitude),
            "longitude": None if p.longitude is None else float(p.longitude),
            "expenses_total": _money(expenses.get(p.id)),
            "scheduled_total": _money(payments.get(p.id, {}).get("SCHEDULED")),
            "paid_total": _money(payments.get(p.id, {}).get("PAID")),
            "latest_report": None if p.id not in latest_reports else {
                "date": latest_reports[p.id].report_date.isoformat(), "summary": latest_reports[p.id].summary},
            "flagged_expenses": flagged.get(p.id, 0),
            "contracts": {"count": count, "total": _money(total), "reported_advance": _money(advance),
                          "advance_on_valued": _money(adv_valued),
                          "reported_balance": _money(balance)},
            "physical": None if not progress else {
                "progress": float(round(progress["done"] / progress["weight"] * 100, 2)) if progress["weight"] else 0.0,
                "planning_complete": abs(progress["weight"] - 100) < Decimal("0.0001"),
                "services": progress["services"]},
        })
    keys = ("expenses_total", "scheduled_total", "paid_total")
    for row in rows:
        row["open_total"] = _money(Decimal(row["expenses_total"]) - Decimal(row["paid_total"]))
    keys = keys + ("open_total",)
    totals = {key: _money(sum(Decimal(row[key]) for row in rows)) for key in keys}
    for key in ("total", "reported_advance", "reported_balance"):
        totals["contracts_" + key] = _money(sum(Decimal(row["contracts"][key]) for row in rows))
    totals["projects"] = sum(1 for row in rows if row["status"] != "COST_POOL")
    totals["measured_projects"] = sum(1 for row in rows if row["physical"])
    return {"projects": rows, "totals": totals}


@router.get("/schedule")
def schedule(start: date | None = Query(None), end: date | None = Query(None), subject: str = Depends(require_identity),
             db: Session = Depends(get_db)):
    """Payments scheduled or paid in [start, end] across all authorized works (weekly FOPAG view).

    Without a period, returns the Monday-to-Sunday week of the latest scheduled payment."""
    ids = [p.id for p in _authorized_projects(db, subject)]
    if (start is None) != (end is None):
        raise HTTPException(status_code=422, detail="Inform both start and end")
    if start is None:
        latest = db.scalar(select(func.max(Payment.scheduled_date)).join(Expense, Payment.expense_id == Expense.id)
                           .where(Expense.project_id.in_(ids))) if ids else None
        if latest is None:
            return {"start": None, "end": None, "items": [], "latest": None}
        start = latest - timedelta(days=latest.weekday())
        end = start + timedelta(days=6)
    if end < start or (end - start) > timedelta(days=92):
        raise HTTPException(status_code=422, detail="Invalid period (max 92 days)")
    if not ids:
        return {"start": start.isoformat(), "end": end.isoformat(), "items": [], "latest": None}
    rows = db.execute(select(Payment, Expense, Project).join(Expense, Payment.expense_id == Expense.id)
                      .join(Project, Expense.project_id == Project.id)
                      .where(Project.id.in_(ids), Payment.scheduled_date >= start, Payment.scheduled_date <= end)
                      .order_by(Payment.scheduled_date, Project.name, Expense.supplier)).all()
    latest = db.scalar(select(func.max(Payment.scheduled_date)).join(Expense, Payment.expense_id == Expense.id)
                       .where(Expense.project_id.in_(ids)))
    return {"start": start.isoformat(), "end": end.isoformat(), "latest": latest.isoformat() if latest else None,
            "items": [{"payment_id": pay.id, "expense_id": exp.id, "project_id": proj.id, "project": proj.name,
                       "project_status": proj.status, "supplier": exp.supplier, "description": exp.description,
                       "category": exp.category, "notes": exp.notes, "amount": _money(pay.amount),
                       "expense_amount": _money(exp.amount), "scheduled_date": pay.scheduled_date.isoformat(),
                       "status": pay.status, "reference": pay.reference} for pay, exp, proj in rows]}


@router.get("/contracts")
def contracts(subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    ids = [p.id for p in _authorized_projects(db, subject)]
    rows = db.execute(select(LaborContract, Project).join(Project, LaborContract.project_id == Project.id)
                      .where(Project.id.in_(ids)).order_by(LaborContract.reported_balance.desc())).all() if ids else []
    return [{"id": c.id, "project_id": p.id, "project": p.name, "contractor": c.contractor, "description": c.description,
             "total": None if c.total is None else _money(c.total), "reported_advance": None if c.reported_advance is None else _money(c.reported_advance),
             "reported_balance": None if c.reported_balance is None else _money(c.reported_balance)} for c, p in rows]


class ProjectDetails(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, min_length=1, max_length=300)
    municipality: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=300)
    status: str | None = None
    responsible: str | None = Field(default=None, max_length=200)
    cost_center: str | None = Field(default=None, max_length=60)
    budget: Decimal | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def check(self):
        if self.status is not None and self.status not in PROJECT_STATUSES:
            raise ValueError("Invalid status")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be informed together")
        return self


@router.patch("/projects/{project_id}")
def update_project(project_id: str, payload: ProjectDetails, subject: str = Depends(require_identity),
                   db: Session = Depends(get_db)):
    project = access(db, subject, project_id, ["OWNER", "ADMIN", "ENGINEER"])
    project = db.scalar(select(Project).where(Project.id == project.id).with_for_update())
    changes = payload.model_dump(exclude_unset=True)
    start = changes.get("start_date", project.start_date)
    end = changes.get("end_date", project.end_date)
    if start and end and end < start:
        raise HTTPException(status_code=422, detail="end_date must be >= start_date")
    if "latitude" in changes or "longitude" in changes:  # typed coordinates: the organization's own data, confirmed by whoever saved them
        from .geo import LocationUpdate, apply_location
        apply_location(project, subject, LocationUpdate(latitude=changes.pop("latitude", None), longitude=changes.pop("longitude", None),
                                                        source="MANUAL"))
        changes["location"] = True
    for field, value in changes.items():
        if field != "location":
            setattr(project, field, value)
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject,
                      action="project.update:" + ",".join(sorted(changes))[:80], resource_id=project.id))
    db.commit()
    return {"id": project.id, "updated": sorted(changes)}


@router.get("/payables")
def payables(subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    """Obligations with outstanding balance: amount owed, scheduled and paid (with evidence) per expense."""
    ids = [p.id for p in _authorized_projects(db, subject)]
    if not ids:
        return []
    paid = (select(Payment.expense_id, Payment.status, func.sum(Payment.amount).label("total"))
            .group_by(Payment.expense_id, Payment.status).subquery())
    sums: dict[str, dict] = {}
    for expense_id, status, total in db.execute(select(paid.c.expense_id, paid.c.status, paid.c.total)).all():
        sums.setdefault(expense_id, {})[status] = total
    rows = db.execute(select(Expense, Project).join(Project, Expense.project_id == Project.id)
                      .where(Project.id.in_(ids)).order_by(Expense.supplier)).all()
    result = []
    for expense, project in rows:
        state = sums.get(expense.id, {})
        paid_total = Decimal(str(state.get("PAID") or 0))
        outstanding = expense.amount - paid_total
        if outstanding <= 0:
            continue
        result.append({"expense_id": expense.id, "project_id": project.id, "project": project.name,
                       "supplier": expense.supplier, "description": expense.description, "category": expense.category,
                       "notes": expense.notes, "amount": _money(expense.amount),
                       "scheduled": _money(state.get("SCHEDULED")), "paid": _money(paid_total),
                       "outstanding": _money(outstanding)})
    return sorted(result, key=lambda row: Decimal(row["outstanding"]), reverse=True)


@router.get("/projects/{project_id}/details")
def project_details(project_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    p = access(db, subject, project_id, READ_ROLES)
    plain = lambda value: None if value is None else str(value)  # noqa: E731
    return {"id": p.id, "name": p.name, "location": p.location, "municipality": p.municipality, "address": p.address,
            "status": p.status, "responsible": p.responsible, "cost_center": p.cost_center, "source": p.source,
            "budget": plain(p.budget), "start_date": plain(p.start_date), "end_date": plain(p.end_date),
            "latitude": plain(p.latitude), "longitude": plain(p.longitude)}
