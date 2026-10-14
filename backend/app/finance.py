from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .db import get_db
from .models import CostEntry, AuditEvent
from .measurements import access
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["finance"])

class CostCreate(BaseModel):
    description: str = Field(min_length=1, max_length=300)
    amount: Decimal = Field(gt=0)

@router.post("/projects/{project_id}/costs", status_code=201)
def create_cost(project_id: str, payload: CostCreate, subject: str = Depends(require_identity),
                db: Session = Depends(get_db)):
    project = access(db, subject, project_id, ["OWNER","ADMIN"])
    item = CostEntry(project_id=project.id, description=payload.description,
                     amount=payload.amount, recorded_by=subject)
    db.add(item); db.flush()
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject,
                      action="cost.create", resource_id=item.id))
    db.commit()
    return {"id":item.id}

@router.get("/projects/{project_id}/finance")
def financial_summary(project_id: str, subject: str = Depends(require_identity),
                      db: Session = Depends(get_db)):
    project = access(db, subject, project_id, ["OWNER","ADMIN","ENGINEER","INSPECTOR","VIEWER"])
    spent = db.scalar(select(func.coalesce(func.sum(CostEntry.amount), 0)).where(CostEntry.project_id == project.id))
    return {"budget":str(project.budget), "spent":str(spent),
            "remaining":str(project.budget-Decimal(str(spent)))}
