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
    item = Measurement(service_item_id=service.id, quantity=payload.quantity, recorded_by=subject)
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
    project = access(db, subject, service.project_id, ["OWNER","ADMIN","INSPECTOR"])
    measurement = db.scalar(select(Measurement).where(
        Measurement.id == measurement_id).with_for_update())
    if measurement.status != "PENDING":
        raise HTTPException(status_code=409, detail="Measurement already decided")
    approved = db.scalar(select(func.coalesce(func.sum(Measurement.quantity), 0)).where(
        Measurement.service_item_id == service.id, Measurement.status == "APPROVED"))
    if Decimal(str(approved)) + measurement.quantity > service.planned_quantity:
        raise HTTPException(status_code=409, detail="Planned quantity exceeded")
    measurement.status = "APPROVED"
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject,
                      action="measurement.approve", resource_id=measurement.id))
    db.commit()
    return {"id":measurement.id,"status":measurement.status}

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
