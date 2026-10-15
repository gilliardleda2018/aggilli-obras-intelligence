from datetime import date, datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .db import get_db
from .models import Project, ServiceItem, Measurement, Membership, AuditEvent
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["measurements"])

def access(db: Session, subject: str, project_id: str, roles: list[str]):
    project = db.scalar(select(Project).join(Membership,
        Membership.organization_id == Project.organization_id).where(
        Project.id == project_id, Membership.subject_id == subject,
        Membership.role.in_(roles)))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    unit: str = Field(min_length=1, max_length=30)
    planned_quantity: Decimal = Field(gt=0)
    weight: Decimal = Field(gt=0, le=100)

class MeasureCreate(BaseModel):
    quantity: Decimal = Field(gt=0)
    measured_on: date | None = None
    notes: str | None = Field(default=None, max_length=500)

class Decision(BaseModel):
    reason: str = Field(min_length=5, max_length=500)

APPROVER_ROLES = ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR"]
READ_ROLES = ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "FIELD_OPERATOR", "VIEWER"]

@router.post("/projects/{project_id}/services", status_code=201)
def create_service(project_id: str, payload: ServiceCreate, subject: str = Depends(require_identity),
                   db: Session = Depends(get_db)):
    project = access(db, subject, project_id, ["OWNER","ADMIN","ENGINEER"])
    db.scalar(select(Project).where(Project.id == project.id).with_for_update())
    existing = db.scalars(select(ServiceItem).where(ServiceItem.project_id == project.id)).all()
    if sum((s.weight for s in existing), Decimal(0)) + payload.weight > 100:
        raise HTTPException(status_code=409, detail="Service weights exceed 100")
    item = ServiceItem(project_id=project.id, **payload.model_dump())
    db.add(item)
    db.flush()
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject,
                      action="service.create", resource_id=item.id))
    db.commit()
    return {"id":item.id}

@router.post("/services/{service_id}/measurements", status_code=201)
def record_measurement(service_id: str, payload: MeasureCreate,
                       subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    service = db.get(ServiceItem, service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    project = access(db, subject, service.project_id, ["OWNER","ADMIN","ENGINEER","FIELD_OPERATOR"])
    if payload.measured_on and payload.measured_on > date.today():
        raise HTTPException(status_code=422, detail="Measurement date cannot be in the future")
    item = Measurement(service_item_id=service.id, quantity=payload.quantity, recorded_by=subject,
                       measured_on=payload.measured_on or date.today(), notes=payload.notes)
    db.add(item)
    db.flush()
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject,
                      action="measurement.record", resource_id=item.id))
    db.commit()
    return {"id":item.id, "status":item.status}

@router.post("/measurements/{measurement_id}/approve")
def approve_measurement(measurement_id: str, subject: str = Depends(require_identity),
                        db: Session = Depends(get_db)):
    # PostgreSQL row locks serialize approvals for the same service.
    measurement = db.get(Measurement, measurement_id)
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    service = db.scalar(select(ServiceItem).where(
        ServiceItem.id == measurement.service_item_id).with_for_update())
    project = access(db, subject, service.project_id, APPROVER_ROLES)
    measurement = db.scalar(select(Measurement).where(
        Measurement.id == measurement_id).with_for_update())
    if measurement.status != "PENDING":
        raise HTTPException(status_code=409, detail="Measurement already decided")
    approved = db.scalar(select(func.coalesce(func.sum(Measurement.quantity), 0)).where(
        Measurement.service_item_id == service.id, Measurement.status == "APPROVED"))
    if Decimal(str(approved)) + measurement.quantity > service.planned_quantity:
        raise HTTPException(status_code=409, detail="Planned quantity exceeded")
    measurement.status = "APPROVED"
    measurement.decided_by = subject
    measurement.decided_at = datetime.now(timezone.utc)
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject,
                      action="measurement.approve", resource_id=measurement.id))
    db.commit()
    return {"id":measurement.id,"status":measurement.status}

@router.post("/measurements/{measurement_id}/reject")
def reject_measurement(measurement_id: str, payload: Decision, subject: str = Depends(require_identity),
                       db: Session = Depends(get_db)):
    measurement = db.get(Measurement, measurement_id)
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    service = db.get(ServiceItem, measurement.service_item_id)
    project = access(db, subject, service.project_id, APPROVER_ROLES)
    measurement = db.scalar(select(Measurement).where(Measurement.id == measurement_id).with_for_update())
    if measurement.status != "PENDING":
        raise HTTPException(status_code=409, detail="Measurement already decided")
    measurement.status = "REJECTED"
    measurement.decided_by = subject
    measurement.decided_at = datetime.now(timezone.utc)
    measurement.decision_reason = payload.reason
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject,
                      action="measurement.reject", resource_id=measurement.id))
    db.commit()
    return {"id": measurement.id, "status": measurement.status}

def _measurement_row(m: Measurement, service: ServiceItem, project: Project) -> dict:
    return {"id": m.id, "project_id": project.id, "project": project.name, "service_id": service.id, "service": service.name,
            "unit": service.unit, "quantity": str(m.quantity), "status": m.status, "recorded_by": m.recorded_by,
            "measured_on": m.measured_on.isoformat() if m.measured_on else None, "notes": m.notes,
            "created_at": m.created_at.isoformat(), "decided_by": m.decided_by,
            "decided_at": m.decided_at.isoformat() if m.decided_at else None, "decision_reason": m.decision_reason}

@router.get("/projects/{project_id}/services")
def list_services(project_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    project = access(db, subject, project_id, READ_ROLES)
    services = db.scalars(select(ServiceItem).where(ServiceItem.project_id == project.id).order_by(ServiceItem.name)).all()
    sums = {(sid, status): qty for sid, status, qty in db.execute(
        select(Measurement.service_item_id, Measurement.status, func.sum(Measurement.quantity))
        .where(Measurement.service_item_id.in_([s.id for s in services])).group_by(Measurement.service_item_id, Measurement.status)).all()}
    rows = []
    for s in services:
        approved = Decimal(str(sums.get((s.id, "APPROVED"), 0)))
        rows.append({"id": s.id, "name": s.name, "unit": s.unit, "planned_quantity": str(s.planned_quantity),
                     "weight": str(s.weight), "approved_quantity": str(approved),
                     "pending_quantity": str(sums.get((s.id, "PENDING"), 0)),
                     "remaining_quantity": str(max(Decimal(0), s.planned_quantity - approved)),
                     "progress": round(float(min(Decimal(1), approved / s.planned_quantity)) * 100, 2)})
    weight = sum((Decimal(r["weight"]) for r in rows), Decimal(0))
    return {"services": rows, "weight_total": str(weight), "weight_available": str(Decimal(100) - weight)}

@router.get("/projects/{project_id}/measurements")
def list_measurements(project_id: str, status: str | None = None, subject: str = Depends(require_identity),
                      db: Session = Depends(get_db)):
    project = access(db, subject, project_id, READ_ROLES)
    query = (select(Measurement, ServiceItem).join(ServiceItem, Measurement.service_item_id == ServiceItem.id)
             .where(ServiceItem.project_id == project.id).order_by(Measurement.created_at.desc()))
    if status:
        query = query.where(Measurement.status == status)
    return [_measurement_row(m, s, project) for m, s in db.execute(query.limit(500)).all()]

@router.get("/measurements/pending")
def pending_measurements(subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    rows = db.execute(select(Measurement, ServiceItem, Project).join(ServiceItem, Measurement.service_item_id == ServiceItem.id)
                      .join(Project, ServiceItem.project_id == Project.id)
                      .join(Membership, Membership.organization_id == Project.organization_id)
                      .where(Membership.subject_id == subject, Membership.role.in_(READ_ROLES), Measurement.status == "PENDING")
                      .order_by(Measurement.created_at)).all()
    return [_measurement_row(m, s, p) for m, s, p in rows]

@router.get("/projects/{project_id}/dashboard")
def dashboard(project_id: str, subject: str = Depends(require_identity),
              db: Session = Depends(get_db)):
    project = access(db, subject, project_id,
                     ["OWNER","ADMIN","ENGINEER","INSPECTOR","FIELD_OPERATOR","VIEWER"])
    services = db.scalars(select(ServiceItem).where(ServiceItem.project_id == project.id)).all()
    rows = []
    for service in services:
        quantity = db.scalar(select(func.coalesce(func.sum(Measurement.quantity),0)).where(
            Measurement.service_item_id == service.id, Measurement.status == "APPROVED"))
        fraction = min(Decimal(1), Decimal(str(quantity))/service.planned_quantity)
        rows.append({"name":service.name,"unit":service.unit,
                     "planned_quantity":str(service.planned_quantity),
                     "approved_quantity":str(quantity),
                     "weight":float(service.weight),
                     "progress":round(float(fraction)*100,2)})
    total_weight = sum(Decimal(str(s["weight"])) for s in rows)
    physical = sum(Decimal(str(s["weight"]))*Decimal(str(s["progress"]))/100 for s in rows)
    return {"id":project.id,"name":project.name,"location":project.location,
            "budget":None if project.budget is None else str(project.budget),
            "physical_progress":round(float(physical/total_weight*100),2) if total_weight else 0,
            "planning_complete":abs(total_weight-100)<Decimal("0.0001"),
            "stages":rows}
