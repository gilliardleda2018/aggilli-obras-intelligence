"""Intelligence API: builds forecast inputs from recorded data, keeps forecast history, returns evolution series."""
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import forecast
from .db import get_db
from .measurements import access
from .models import Expense, ForecastRun, Measurement, Membership, Payment, Project, ServiceItem
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["intelligence"])
READ_ROLES = ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "FIELD_OPERATOR", "VIEWER"]


def build_inputs(db: Session, project: Project, today: date | None = None) -> forecast.ProjectInputs:
    services = db.scalars(select(ServiceItem).where(ServiceItem.project_id == project.id)).all()
    weight_total = sum((s.weight for s in services), Decimal(0))
    measurements = db.execute(select(Measurement.service_item_id, Measurement.quantity, Measurement.measured_on, Measurement.created_at)
                              .where(Measurement.service_item_id.in_([s.id for s in services]), Measurement.status == "APPROVED")).all()
    by_date: dict[date, list] = defaultdict(list)
    for service_id, quantity, measured_on, created_at in measurements:
        by_date[measured_on or created_at.date()].append((service_id, quantity))
    done = defaultdict(Decimal)
    planned = {s.id: s for s in services}
    progress = []
    for day in sorted(by_date):
        for service_id, quantity in by_date[day]:
            done[service_id] += quantity
        value = sum((planned[sid].weight * min(Decimal(1), qty / planned[sid].planned_quantity) for sid, qty in done.items()), Decimal(0))
        progress.append((day, float(value / weight_total * 100) if weight_total else 0.0))
    service_rows = [{"name": s.name, "weight": float(s.weight),
                     "progress": round(float(min(Decimal(1), done[s.id] / s.planned_quantity)) * 100, 1)} for s in services]

    expenses = db.execute(select(Expense.expense_date, Expense.amount).where(Expense.project_id == project.id,
                                                                            Expense.expense_date.is_not(None))).all()
    per_day = defaultdict(Decimal)
    for day, amount in expenses:
        per_day[day] += amount
    running, costs = Decimal(0), []
    for day in sorted(per_day):
        running += per_day[day]
        costs.append((day, float(running)))
    return forecast.ProjectInputs(start_date=project.start_date, end_date=project.end_date,
                                  budget=float(project.budget) if project.budget is not None else None, progress=progress,
                                  costs=costs, planning_complete=bool(services) and abs(weight_total - 100) < Decimal("0.0001"),
                                  services=service_rows, today=today or date.today())


def _record(db: Session, project_id: str, kind: str, digest: str, result: dict) -> None:
    exists = db.scalar(select(ForecastRun.id).where(ForecastRun.project_id == project_id, ForecastRun.kind == kind,
                                                    ForecastRun.model == result["model"], ForecastRun.version == result["version"],
                                                    ForecastRun.input_hash == digest))
    if not exists:
        db.add(ForecastRun(project_id=project_id, kind=kind, model=result["model"], version=result["version"], input_hash=digest,
                           status=result["status"], result=json.dumps(result, ensure_ascii=False)))


def project_intelligence(db: Session, project: Project) -> dict:
    inputs = build_inputs(db, project)
    digest = inputs.digest()
    schedule = forecast.schedule_forecast(inputs)
    cost = forecast.cost_forecast(inputs)
    _record(db, project.id, "schedule", digest, schedule)
    _record(db, project.id, "cost", digest, cost)
    return {"inputs": inputs, "schedule": schedule, "cost": cost}


def _cash(db: Session, project_ids: list[str], weeks: int = 8) -> list[dict]:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    rows = db.execute(select(Payment.scheduled_date, Payment.amount).join(Expense, Payment.expense_id == Expense.id)
                      .where(Expense.project_id.in_(project_ids), Payment.status == "SCHEDULED",
                             Payment.scheduled_date >= monday, Payment.scheduled_date < monday + timedelta(weeks=weeks))).all()
    buckets = [{"week_start": str(monday + timedelta(weeks=i)), "scheduled": Decimal(0)} for i in range(weeks)]
    for day, amount in rows:
        buckets[(day - monday).days // 7]["scheduled"] += amount
    overdue = sum((amount for (amount,) in db.execute(
        select(Payment.amount).join(Expense, Payment.expense_id == Expense.id)
        .where(Expense.project_id.in_(project_ids), Payment.status == "SCHEDULED", Payment.scheduled_date < monday)).all()), Decimal(0))
    return [{"week_start": b["week_start"], "scheduled": str(b["scheduled"])} for b in buckets] + [{"overdue_scheduled": str(overdue)}]


@router.get("/projects/{project_id}/intelligence")
def get_project_intelligence(project_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    project = access(db, subject, project_id, READ_ROLES)
    data = project_intelligence(db, project)
    db.commit()
    inputs = data["inputs"]
    history = db.scalars(select(ForecastRun).where(ForecastRun.project_id == project.id)
                         .order_by(ForecastRun.created_at.desc()).limit(40)).all()
    baseline = []
    if project.start_date and project.end_date:
        step = max(1, (project.end_date - project.start_date).days // 20)
        day = project.start_date
        while day <= project.end_date:
            baseline.append({"date": str(day), "progress": forecast._baseline_pct(inputs, day)})
            day += timedelta(days=step)
        baseline.append({"date": str(project.end_date), "progress": 100.0})
    return {"schedule": data["schedule"], "cost": data["cost"],
            "series": {"progress": [{"date": str(d), "progress": round(v, 2)} for d, v in inputs.progress],
                       "cost": [{"date": str(d), "cost": round(v, 2)} for d, v in inputs.costs], "baseline": baseline},
            "cash": _cash(db, [project.id]),
            "history": [{"kind": h.kind, "model": h.model, "version": h.version, "status": h.status, "created_at": h.created_at.isoformat(),
                         "summary": _summary(h.kind, json.loads(h.result))} for h in history]}


def _summary(kind: str, result: dict) -> dict:
    if kind == "schedule":
        return {key: result.get(key) for key in ("finish_p50", "finish_p10", "finish_p90", "probability_on_time", "current_progress")}
    return {key: result.get(key) for key in ("eac_p50", "eac_low", "eac_high", "actual_cost", "physical_progress", "cpi")}


@router.get("/intelligence/portfolio")
def portfolio_intelligence(subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).join(Membership, Membership.organization_id == Project.organization_id)
                          .where(Membership.subject_id == subject, Membership.role.in_(READ_ROLES), Project.status != "COST_POOL")
                          .order_by(Project.name)).all()
    rows = []
    for project in projects:
        data = project_intelligence(db, project)
        s, c = data["schedule"], data["cost"]
        rows.append({"id": project.id, "name": project.name, "status": project.status, "source": project.source,
                     "schedule": {key: s.get(key) for key in ("status", "missing", "current_progress", "finish_p10", "finish_p50",
                                                               "finish_p90", "probability_on_time", "delay_days_p50", "contract_end",
                                                               "model", "version")},
                     "cost": {key: c.get(key) for key in ("status", "missing", "actual_cost", "eac_p50", "eac_low", "eac_high", "cpi",
                                                           "budget", "model", "version")}})
    db.commit()
    return {"projects": rows, "cash": _cash(db, [p.id for p in projects]) if projects else []}
