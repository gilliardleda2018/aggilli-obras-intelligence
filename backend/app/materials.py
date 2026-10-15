"""Materials and stock: balance at moving average cost, consumption vs. measured progress, coverage forecast."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import get_db
from .measurements import access
from .models import AuditEvent, Expense, Material, Measurement, Membership, Project, ServiceItem, StockMovement
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["materials"])
READ_ROLES = ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "FIELD_OPERATOR", "VIEWER"]
ZERO = Decimal(0)
OVERCONSUMPTION = Decimal("1.15")   # consumption above 115% of what the measured progress justifies
COVERAGE_WARNING_DAYS = 7


class MaterialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    unit: str = Field(min_length=1, max_length=30)
    category: str | None = Field(default=None, max_length=60)
    min_stock: Decimal | None = Field(default=None, ge=0)
    planned_quantity: Decimal | None = Field(default=None, gt=0)
    service_id: str | None = None


class MaterialUpdate(BaseModel):
    category: str | None = Field(default=None, max_length=60)
    min_stock: Decimal | None = Field(default=None, ge=0)
    planned_quantity: Decimal | None = Field(default=None, gt=0)
    service_id: str | None = None


class MovementCreate(BaseModel):
    quantity: Decimal = Field(gt=0)
    kind: str
    movement_date: date | None = None
    unit_cost: Decimal | None = Field(default=None, ge=0)
    supplier: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=300)
    create_expense: bool = False   # purchase not yet recorded as an expense → record it now (feeds costs/forecasts)


def _service_progress(db: Session, service_ids: list[str]) -> dict[str, Decimal]:
    if not service_ids:
        return {}
    approved = dict(db.execute(select(Measurement.service_item_id, func.sum(Measurement.quantity))
                               .where(Measurement.service_item_id.in_(service_ids), Measurement.status == "APPROVED")
                               .group_by(Measurement.service_item_id)).all())
    return {s.id: min(Decimal(1), Decimal(str(approved.get(s.id) or 0)) / s.planned_quantity)
            for s in db.scalars(select(ServiceItem).where(ServiceItem.id.in_(service_ids))).all()}


def material_rows(db: Session, materials: list[Material], today: date | None = None) -> list[dict]:
    today = today or date.today()
    if not materials:
        return []
    movements = db.scalars(select(StockMovement).where(StockMovement.material_id.in_([m.id for m in materials]))
                           .order_by(StockMovement.movement_date, StockMovement.created_at)).all()
    by_material: dict[str, list[StockMovement]] = {}
    for mv in movements:
        by_material.setdefault(mv.material_id, []).append(mv)
    service_ids = [m.service_id for m in materials if m.service_id]
    progress = _service_progress(db, service_ids)
    services = {s.id: s.name for s in db.scalars(select(ServiceItem).where(ServiceItem.id.in_(service_ids))).all()} if service_ids else {}
    rows = []
    for m in materials:
        balance, avg_cost, consumed, consumed_value, recent_out, purchased = ZERO, None, ZERO, ZERO, ZERO, ZERO
        for mv in by_material.get(m.id, []):
            day = mv.movement_date or mv.created_at.date()
            if mv.kind == "IN":
                if mv.unit_cost is not None:
                    avg_cost = mv.unit_cost if avg_cost is None or balance <= 0 else \
                        (balance * avg_cost + mv.quantity * mv.unit_cost) / (balance + mv.quantity)
                balance += mv.quantity
                purchased += mv.quantity
            else:
                balance -= mv.quantity
                consumed += mv.quantity
                consumed_value += mv.quantity * (avg_cost or ZERO)
                if day >= today - timedelta(days=30):
                    recent_out += mv.quantity
        daily = recent_out / 30
        coverage = int(balance / daily) if daily > 0 else None
        expected = (m.planned_quantity * progress[m.service_id]) if (m.planned_quantity and m.service_id in progress) else None
        flags = []
        if m.min_stock is not None and balance < m.min_stock:
            flags.append("estoque_baixo")
        if coverage is not None and coverage <= COVERAGE_WARNING_DAYS:
            flags.append("ruptura_proxima")
        if expected is not None and expected > 0 and consumed > expected * OVERCONSUMPTION:
            flags.append("consumo_acima")
        rows.append({"id": m.id, "project_id": m.project_id, "name": m.name, "unit": m.unit, "category": m.category,
                     "balance": str(balance), "min_stock": None if m.min_stock is None else str(m.min_stock),
                     "avg_cost": None if avg_cost is None else str(avg_cost.quantize(Decimal("0.0001"))),
                     "stock_value": str((balance * (avg_cost or ZERO)).quantize(Decimal("0.01"))),
                     "purchased": str(purchased), "consumed": str(consumed), "consumed_value": str(consumed_value.quantize(Decimal("0.01"))),
                     "daily_consumption_30d": str(daily.quantize(Decimal("0.001"))), "coverage_days": coverage,
                     "planned_quantity": None if m.planned_quantity is None else str(m.planned_quantity),
                     "service_id": m.service_id, "service": services.get(m.service_id),
                     "service_progress": None if m.service_id not in progress else round(float(progress[m.service_id]) * 100, 2),
                     "expected_consumption": None if expected is None else str(expected.quantize(Decimal("0.001"))), "flags": flags})
    return rows


@router.post("/projects/{project_id}/materials", status_code=201)
def create_material(project_id: str, payload: MaterialCreate, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    project = access(db, subject, project_id, ["OWNER", "ADMIN", "ENGINEER"])
    if payload.service_id and db.scalar(select(ServiceItem.project_id).where(ServiceItem.id == payload.service_id)) != project.id:
        raise HTTPException(status_code=422, detail="Service does not belong to this project")
    material = Material(project_id=project.id, **payload.model_dump())
    db.add(material); db.flush()
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject, action="material.create", resource_id=material.id))
    db.commit()
    return {"id": material.id}


@router.patch("/materials/{material_id}")
def update_material(material_id: str, payload: MaterialUpdate, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    project = access(db, subject, material.project_id, ["OWNER", "ADMIN", "ENGINEER"])
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("service_id") and db.scalar(select(ServiceItem.project_id).where(ServiceItem.id == changes["service_id"])) != project.id:
        raise HTTPException(status_code=422, detail="Service does not belong to this project")
    for field, value in changes.items():
        setattr(material, field, value)
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject, action="material.update", resource_id=material.id))
    db.commit()
    return {"id": material.id, "updated": sorted(changes)}


@router.post("/materials/{material_id}/movements", status_code=201)
def movement(material_id: str, payload: MovementCreate, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    material = db.scalar(select(Material).where(Material.id == material_id).with_for_update())
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    project = access(db, subject, material.project_id, ["OWNER", "ADMIN", "ENGINEER", "FIELD_OPERATOR"])
    if payload.kind not in ("IN", "OUT"):
        raise HTTPException(status_code=422, detail="Invalid movement kind")
    if payload.movement_date and payload.movement_date > date.today():
        raise HTTPException(status_code=422, detail="Movement date cannot be in the future")
    movements = db.scalars(select(StockMovement).where(StockMovement.material_id == material.id)).all()
    balance = sum((m.quantity if m.kind == "IN" else -m.quantity for m in movements), Decimal(0))
    if payload.kind == "OUT" and balance < payload.quantity:
        raise HTTPException(status_code=409, detail="Insufficient stock")
    expense_id = None
    if payload.kind == "IN" and payload.create_expense:
        if payload.unit_cost is None or not payload.supplier:
            raise HTTPException(status_code=422, detail="Unit cost and supplier are required to record the purchase as an expense")
        expense = Expense(project_id=project.id, supplier=payload.supplier,
                          description=f"Compra de {material.name} ({payload.quantity} {material.unit})",
                          amount=(payload.quantity * payload.unit_cost).quantize(Decimal("0.01")), category="MATERIAL", status="OPEN",
                          created_by=subject, expense_date=payload.movement_date or date.today(), notes=payload.note)
        db.add(expense); db.flush()
        expense_id = expense.id
        db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject, action="expense.from_stock_entry", resource_id=expense.id))
    item = StockMovement(material_id=material.id, kind=payload.kind, quantity=payload.quantity, recorded_by=subject,
                         movement_date=payload.movement_date or date.today(), unit_cost=payload.unit_cost, supplier=payload.supplier,
                         note=payload.note, expense_id=expense_id)
    db.add(item); db.flush()
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject, action="stock." + payload.kind.lower(), resource_id=item.id))
    db.commit()
    return {"id": item.id, "balance": str(balance + (payload.quantity if payload.kind == "IN" else -payload.quantity)), "expense_id": expense_id}


@router.get("/projects/{project_id}/materials")
def list_materials(project_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    access(db, subject, project_id, READ_ROLES)
    materials = db.scalars(select(Material).where(Material.project_id == project_id).order_by(Material.name)).all()
    return material_rows(db, list(materials))


@router.get("/materials/overview")
def materials_overview(subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    projects = {p.id: p for p in db.scalars(select(Project).join(Membership, Membership.organization_id == Project.organization_id)
                                             .where(Membership.subject_id == subject, Membership.role.in_(READ_ROLES))).all()}
    materials = db.scalars(select(Material).where(Material.project_id.in_(list(projects))).order_by(Material.name)).all() if projects else []
    rows = material_rows(db, list(materials))
    for row in rows:
        row["project"] = projects[row["project_id"]].name
    return {"materials": rows, "stock_value": str(sum((Decimal(r["stock_value"]) for r in rows), ZERO)),
            "flagged": sum(1 for r in rows if r["flags"])}


@router.get("/materials/{material_id}/movements")
def list_movements(material_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    access(db, subject, material.project_id, READ_ROLES)
    rows = db.scalars(select(StockMovement).where(StockMovement.material_id == material.id)
                      .order_by(StockMovement.movement_date.desc(), StockMovement.created_at.desc()).limit(500)).all()
    return [{"id": r.id, "kind": r.kind, "quantity": str(r.quantity), "date": str(r.movement_date or r.created_at.date()),
             "unit_cost": None if r.unit_cost is None else str(r.unit_cost), "supplier": r.supplier, "note": r.note,
             "expense_id": r.expense_id, "recorded_by": r.recorded_by} for r in rows]
