from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .db import get_db
from .models import Material, StockMovement, Project, AuditEvent
from .measurements import access
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["materials"])

class MaterialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    unit: str = Field(min_length=1, max_length=30)

class MovementCreate(BaseModel):
    quantity: Decimal = Field(gt=0)
    kind: str

@router.post("/projects/{project_id}/materials", status_code=201)
def create_material(project_id: str, payload: MaterialCreate, subject: str = Depends(require_identity),
                    db: Session = Depends(get_db)):
    project = access(db, subject, project_id, ["OWNER","ADMIN","ENGINEER"])
    material = Material(project_id=project.id, **payload.model_dump())
    db.add(material); db.flush()
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject,
                      action="material.create", resource_id=material.id))
    db.commit()
    return {"id": material.id}

@router.post("/materials/{material_id}/movements", status_code=201)
def movement(material_id: str, payload: MovementCreate, subject: str = Depends(require_identity),
             db: Session = Depends(get_db)):
    material = db.scalar(select(Material).where(Material.id == material_id).with_for_update())
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    project = access(db, subject, material.project_id, ["OWNER","ADMIN","ENGINEER","FIELD_OPERATOR"])
    if payload.kind not in ("IN","OUT"):
        raise HTTPException(status_code=422, detail="Invalid movement kind")
    movements = db.scalars(select(StockMovement).where(StockMovement.material_id == material.id)).all()
    balance = sum((m.quantity if m.kind == "IN" else -m.quantity for m in movements), Decimal(0))
    if payload.kind == "OUT" and balance < payload.quantity:
        raise HTTPException(status_code=409, detail="Insufficient stock")
    item = StockMovement(material_id=material.id, kind=payload.kind, quantity=payload.quantity,
                         recorded_by=subject)
    db.add(item); db.flush()
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject,
                      action="stock."+payload.kind.lower(), resource_id=item.id))
    db.commit()
    return {"id":item.id, "balance":str(balance + (payload.quantity if payload.kind == "IN" else -payload.quantity))}

@router.get("/projects/{project_id}/materials")
def list_materials(project_id: str, subject: str = Depends(require_identity),
                   db: Session = Depends(get_db)):
    access(db, subject, project_id, ["OWNER","ADMIN","ENGINEER","INSPECTOR","FIELD_OPERATOR","VIEWER"])
    materials = db.scalars(select(Material).where(Material.project_id == project_id)).all()
    return [{"id":m.id,"name":m.name,"unit":m.unit} for m in materials]
