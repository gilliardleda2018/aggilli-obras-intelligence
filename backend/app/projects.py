from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import Membership, Project, AuditEvent
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["projects"])

class ProjectCreate(BaseModel):
    organization_id: str
    name: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=300)
    budget: Decimal = Field(ge=0)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def check_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self

@router.post("/projects", status_code=201)
def create_project(payload: ProjectCreate, subject_id: str = Depends(require_identity),
                   db: Session = Depends(get_db)):
    membership = db.scalar(select(Membership).where(
        Membership.organization_id == payload.organization_id,
        Membership.subject_id == subject_id,
        Membership.role.in_(["OWNER", "ADMIN", "ENGINEER"])
    ))
    if membership is None:
        raise HTTPException(status_code=403, detail="Access denied")
    project = Project(**payload.model_dump())
    db.add(project)
    db.flush()
    db.add(AuditEvent(organization_id=payload.organization_id, subject_id=subject_id,
                      action="project.create", resource_id=project.id))
    db.commit()
    return {"id": project.id, "name": project.name}

@router.get("/projects")
def list_projects(subject_id: str = Depends(require_identity), db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).join(Membership,
        Project.organization_id == Membership.organization_id).where(
        Membership.subject_id == subject_id)).all()
    return [{"id": p.id, "name": p.name, "location": p.location,
             "budget": str(p.budget)} for p in projects]
