"""Automatic alerts and weekly trends, recomputed from the recorded data.

Business rules are the first barrier; robust statistics (median/MAD, quartiles) support them. Every alert
carries its reason and the records behind it, and people mark it as confirmed, false alarm or resolved —
decisions are stored (they never delete the alert's evidence) to tune the detectors. An anomaly is a
signal to check, never an accusation.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from statistics import median

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .classifier import normalize
from .db import get_db
from .intelligence import project_intelligence
from .materials import material_rows
from .models import AlertReview, AuditEvent, Expense, Material, Measurement, Membership, Payment, Project, ServiceItem
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["alerts"])
READ_ROLES = ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "FIELD_OPERATOR", "VIEWER"]
REVIEW_ROLES = ["OWNER", "ADMIN", "ENGINEER"]
SEVERITY = {"high": 0, "medium": 1, "low": 2}


def brl(value) -> str:
    text = f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + text


def _br_date(iso) -> str:
    return iso.strftime("%d/%m/%Y") if hasattr(iso, "strftime") else "/".join(reversed(str(iso).split("-")))


def _projects(db: Session, subject: str) -> list[Project]:
    return list(db.scalars(select(Project).join(Membership, Membership.organization_id == Project.organization_id)
                           .where(Membership.subject_id == subject, Membership.role.in_(READ_ROLES))).all())


def _alert(key, kind, severity, project, title, detail, evidence=None):
    return {"key": key, "type": kind, "severity": severity, "project_id": project.id, "project": project.name,
            "organization_id": project.organization_id, "title": title, "detail": detail, "evidence": evidence or []}


def detect(db: Session, projects: list[Project], today: date | None = None) -> list[dict]:
    today = today or date.today()
    by_id = {p.id: p for p in projects}
    alerts: list[dict] = []
    expenses = db.scalars(select(Expense).where(Expense.project_id.in_(list(by_id)))).all() if by_id else []

    # 1) Possible duplicates: same supplier and amount within 7 days, different entries.
    groups = defaultdict(list)
    for e in expenses:
        groups[(normalize(e.supplier), e.amount)].append(e)
    for (_, amount), items in groups.items():
        items.sort(key=lambda e: (e.expense_date or date.min, e.id))
        for a, b in zip(items, items[1:]):
            close = a.expense_date and b.expense_date and abs((b.expense_date - a.expense_date).days) <= 7
            if close or (a.expense_date is None and b.expense_date is None):
                project = by_id[b.project_id]
                alerts.append(_alert(f"dup:{a.id}:{b.id}", "possivel_duplicidade", "high", project,
                                     f"Possível despesa duplicada — {b.supplier}",
                                     f"Dois lançamentos de {brl(amount)} para o mesmo fornecedor com até 7 dias de diferença.",
                                     [{"kind": "expense", "id": x.id, "label": f"{x.description} · {x.expense_date or 'sem data'}"} for x in (a, b)]))

    # 2) Unusual values: robust z-score per supplier (≥5 entries) or quartiles per category (≥10 entries).
    flagged = set()
    by_supplier = defaultdict(list)
    for e in expenses:
        by_supplier[normalize(e.supplier)].append(e)
    for items in by_supplier.values():
        if len(items) < 5:
            continue
        values = [float(e.amount) for e in items]
        med = median(values)
        mad = median([abs(v - med) for v in values])
        for e in items:
            z = 0.6745 * (float(e.amount) - med) / mad if mad else 0
            if z > 3.5 or (not mad and float(e.amount) > 3 * med > 0):
                flagged.add(e.id)
                alerts.append(_alert(f"outlier:{e.id}", "valor_incomum", "medium", by_id[e.project_id],
                                     f"Valor incomum para {e.supplier}", f"{brl(e.amount)} contra mediana de {brl(med)} deste fornecedor.",
                                     [{"kind": "expense", "id": e.id, "label": e.description}]))
    by_category = defaultdict(list)
    for e in expenses:
        by_category[e.category].append(e)
    for category, items in by_category.items():
        if len(items) < 10:
            continue
        values = sorted(float(e.amount) for e in items)
        q1, q3 = values[len(values) // 4], values[(3 * len(values)) // 4]
        limit = q3 + 3 * (q3 - q1)
        for e in items:
            if e.id not in flagged and float(e.amount) > limit > 0:
                alerts.append(_alert(f"outlier:{e.id}", "valor_incomum", "low", by_id[e.project_id],
                                     f"Valor alto para a categoria — {e.supplier}",
                                     f"{brl(e.amount)} acima do limite estatístico de {brl(limit)} para a categoria.",
                                     [{"kind": "expense", "id": e.id, "label": e.description}]))

    # 3) Payments scheduled in the past and still not confirmed.
    overdue = db.execute(select(Payment, Expense).join(Expense, Payment.expense_id == Expense.id)
                         .where(Expense.project_id.in_(list(by_id)), Payment.status == "SCHEDULED",
                                Payment.scheduled_date < today - timedelta(days=3))).all() if by_id else []
    per_project = defaultdict(list)
    for payment, expense in overdue:
        per_project[expense.project_id].append((payment, expense))
    for project_id, items in per_project.items():
        total = sum(float(p.amount) for p, _ in items)
        oldest = min(p.scheduled_date for p, _ in items)
        alerts.append(_alert(f"overdue:{project_id}:{'-'.join(sorted(p.id[:8] for p, _ in items))}", "pagamento_vencido", "medium",
                             by_id[project_id], f"{len(items)} pagamento(s) programado(s) sem confirmação",
                             f"{brl(total)} programados desde {oldest:%d/%m/%Y}: confirme com comprovante ou reprograme.",
                             [{"kind": "payment", "id": p.id, "label": f"{e.supplier} · {brl(p.amount)}"} for p, e in items]))

    # 4) Measurements waiting for approval for more than 7 days.
    pending = db.execute(select(Measurement, ServiceItem).join(ServiceItem, Measurement.service_item_id == ServiceItem.id)
                         .where(ServiceItem.project_id.in_(list(by_id)), Measurement.status == "PENDING")).all() if by_id else []
    for measurement, service in pending:
        age = (today - (measurement.measured_on or measurement.created_at.date())).days
        if age > 7:
            alerts.append(_alert(f"pending:{measurement.id}", "medicao_parada", "low", by_id[service.project_id],
                                 f"Medição aguardando aprovação há {age} dias", f"{service.name}: {measurement.quantity} {service.unit}.",
                                 [{"kind": "measurement", "id": measurement.id, "label": service.name}]))

    # 5) Materials: low stock, stockout within a week, consumption above what the measured progress justifies.
    materials = db.scalars(select(Material).where(Material.project_id.in_(list(by_id)))).all() if by_id else []
    for row in material_rows(db, list(materials), today):
        project = by_id[row["project_id"]]
        if "consumo_acima" in row["flags"]:
            alerts.append(_alert(f"consumption:{row['id']}:{row['consumed']}", "consumo_acima", "high", project,
                                 f"Consumo de {row['name']} acima do avanço medido",
                                 f"Consumido {row['consumed']} {row['unit']} contra {row['expected_consumption']} esperados para "
                                 f"{row['service_progress']}% de {row['service']}: verifique perdas, desvio ou quantitativo.",
                                 [{"kind": "material", "id": row["id"], "label": row["name"]}]))
        if "ruptura_proxima" in row["flags"]:
            alerts.append(_alert(f"stockout:{row['id']}:{today.isocalendar()[1]}", "ruptura_proxima", "medium", project,
                                 f"{row['name']} acaba em cerca de {row['coverage_days']} dias",
                                 f"Saldo {row['balance']} {row['unit']} e consumo médio de {row['daily_consumption_30d']} {row['unit']}/dia: programe a compra.",
                                 [{"kind": "material", "id": row["id"], "label": row["name"]}]))
        elif "estoque_baixo" in row["flags"]:
            alerts.append(_alert(f"lowstock:{row['id']}:{today.isocalendar()[1]}", "estoque_baixo", "low", project,
                                 f"Estoque de {row['name']} abaixo do mínimo",
                                 f"Saldo {row['balance']} {row['unit']} contra mínimo de {row['min_stock']}.",
                                 [{"kind": "material", "id": row["id"], "label": row["name"]}]))

    # 6) Forecast-based risks and stale data, per work in progress.
    for project in projects:
        if project.status != "IN_PROGRESS":
            continue
        data = project_intelligence(db, project)
        s, c, inputs = data["schedule"], data["cost"], data["inputs"]
        if s["status"] == "ok":
            if s.get("probability_on_time") is not None and s["probability_on_time"] < 0.5:
                alerts.append(_alert(f"delay:{project.id}", "risco_atraso", "high" if s["probability_on_time"] < 0.2 else "medium", project,
                                     "Risco de atraso", f"Término provável {_br_date(s['finish_p50'])} ({round(s['probability_on_time'] * 100)}% de chance de cumprir o contrato)."))
            productivity = s.get("productivity") or {}
            if productivity.get("average_pp_per_week") and productivity["recent_pp_per_week"] < 0.6 * productivity["average_pp_per_week"]:
                alerts.append(_alert(f"productivity:{project.id}:{inputs.progress[-1][0]}", "queda_produtividade", "medium", project,
                                     "Queda de produtividade", f"Ritmo recente de {productivity['recent_pp_per_week']} p.p./semana contra média de "
                                     f"{productivity['average_pp_per_week']}."))
        if c["status"] == "ok" and (c.get("cpi") is not None and c["cpi"] < 0.9 or (c.get("budget") and c["eac_p50"] > c["budget"] * 1.05)):
            alerts.append(_alert(f"cost:{project.id}", "risco_estouro", "high", project, "Risco de estouro do orçamento",
                                 f"Custo final estimado {brl(c['eac_p50'])}" + (f" contra orçamento de {brl(c['budget'])}" if c.get("budget") else "") + "."))
        last_measure = inputs.progress[-1][0] if inputs.progress else None
        if inputs.planning_complete and (not last_measure or (today - last_measure).days > 21):
            alerts.append(_alert(f"stale-measure:{project.id}:{today.isocalendar()[1]}", "sem_medicao_recente", "low", project,
                                 "Sem medição recente", "Mais de 21 dias sem medição aprovada: o avanço e as previsões ficam desatualizados."))
    return sorted(alerts, key=lambda a: (SEVERITY[a["severity"]], a["project"], a["title"]))


@router.get("/alerts")
def list_alerts(include_reviewed: bool = False, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    projects = _projects(db, subject)
    alerts = detect(db, projects)
    reviews = {(r.organization_id, r.alert_key): r for r in db.scalars(select(AlertReview).where(
        AlertReview.organization_id.in_({p.organization_id for p in projects}))).all()} if projects else {}
    db.commit()
    result = []
    for alert in alerts:
        review = reviews.get((alert["organization_id"], alert["key"]))
        alert["review"] = None if not review else {"decision": review.decision, "note": review.note, "by": review.reviewed_by,
                                                   "at": review.reviewed_at.isoformat()}
        if include_reviewed or not review:
            result.append(alert)
    feedback = defaultdict(lambda: {"confirmed": 0, "false_alarm": 0})
    for review in reviews.values():
        key = "confirmed" if review.decision == "CONFIRMED" else "false_alarm" if review.decision == "FALSE_ALARM" else None
        if key:
            feedback[review.alert_type][key] += 1
    return {"alerts": result, "open": sum(1 for a in alerts if not a["review"]), "feedback": feedback}


class Review(BaseModel):
    decision: str = Field(pattern="^(CONFIRMED|FALSE_ALARM|RESOLVED)$")
    note: str | None = Field(default=None, max_length=500)


@router.post("/alerts/{alert_key:path}/review")
def review_alert(alert_key: str, payload: Review, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    projects = [p for p in _projects(db, subject)]
    alert = next((a for a in detect(db, projects) if a["key"] == alert_key), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    role = db.scalar(select(Membership.role).where(Membership.subject_id == subject, Membership.organization_id == alert["organization_id"]))
    if role not in REVIEW_ROLES:
        raise HTTPException(status_code=404, detail="Alert not found")
    review = db.scalar(select(AlertReview).where(AlertReview.organization_id == alert["organization_id"], AlertReview.alert_key == alert_key))
    if review is None:
        review = AlertReview(organization_id=alert["organization_id"], alert_key=alert_key, alert_type=alert["type"],
                             decision=payload.decision, reviewed_by=subject)
        db.add(review)
    review.decision, review.note, review.reviewed_by = payload.decision, payload.note, subject
    review.reviewed_at = datetime.now(timezone.utc)
    db.add(AuditEvent(organization_id=alert["organization_id"], subject_id=subject, action="alert.review:" + payload.decision,
                      resource_id=alert["project_id"]))
    db.commit()
    return {"key": alert_key, "decision": payload.decision}


@router.get("/trends")
def trends(weeks: int = Query(12, ge=4, le=52), project_id: str | None = None, subject: str = Depends(require_identity),
           db: Session = Depends(get_db)):
    """Weekly evolution: incurred cost by category, paid and scheduled payments, entries recorded."""
    projects = _projects(db, subject)
    ids = [p.id for p in projects if project_id in (None, p.id)]
    if project_id and not ids:
        raise HTTPException(status_code=404, detail="Project not found")
    today = date.today()
    first = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)
    buckets = [{"week_start": str(first + timedelta(weeks=i)), "incurred": defaultdict(Decimal), "paid": Decimal(0),
                "scheduled": Decimal(0), "entries": 0} for i in range(weeks)]

    def slot(day: date | None):
        if not day or day < first:
            return None
        index = (day - first).days // 7
        return buckets[index] if index < weeks else None

    if ids:
        for e in db.scalars(select(Expense).where(Expense.project_id.in_(ids))).all():
            bucket = slot(e.expense_date)
            if bucket:
                bucket["incurred"][e.category] += e.amount
                bucket["entries"] += 1
        for p, in db.execute(select(Payment).join(Expense, Payment.expense_id == Expense.id).where(Expense.project_id.in_(ids))).all():
            bucket = slot(p.scheduled_date)
            if bucket:
                bucket["paid" if p.status == "PAID" else "scheduled"] += p.amount
    return {"weeks": [{"week_start": b["week_start"], "incurred": {k: str(v) for k, v in b["incurred"].items()},
                       "incurred_total": str(sum(b["incurred"].values(), Decimal(0))), "paid": str(b["paid"]),
                       "scheduled": str(b["scheduled"]), "entries": b["entries"]} for b in buckets]}
