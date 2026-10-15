from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import FieldReport, Inspection, AuditEvent
from .measurements import access
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["field"])

class ReportCreate(BaseModel):
    report_date: date
    weather: str = Field(max_length=100)
    summary: str = Field(min_length=1, max_length=5000)

class InspectionCreate(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    status: str = Field(pattern="^(OPEN|RESOLVED)$")

@router.post("/projects/{project_id}/field-reports", status_code=201)
def add_report(project_id: str, payload: ReportCreate, subject: str = Depends(require_identity),
               db: Session = Depends(get_db)):
    project = access(db, subject, project_id, ["OWNER","ADMIN","ENGINEER","FIELD_OPERATOR"])
    report = FieldReport(project_id=project.id, recorded_by=subject, **payload.model_dump())
    db.add(report); db.flush()
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject,
                      action="field_report.create", resource_id=report.id))
    db.commit()
    return {"id":report.id}

@router.get("/projects/{project_id}/field-reports")
def reports(project_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    access(db, subject, project_id, ["OWNER","ADMIN","ENGINEER","INSPECTOR","FIELD_OPERATOR","VIEWER"])
    rows = db.scalars(select(FieldReport).where(FieldReport.project_id == project_id)
                      .order_by(FieldReport.report_date.desc())).all()
    return [{"id":r.id,"date":r.report_date.isoformat(),"weather":r.weather,
             "summary":r.summary} for r in rows]

@router.post("/projects/{project_id}/inspections", status_code=201)
def add_inspection(project_id: str, payload: InspectionCreate,
                   subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    project = access(db, subject, project_id, ["OWNER","ADMIN","ENGINEER","INSPECTOR"])
    inspection = Inspection(project_id=project.id, recorded_by=subject, **payload.model_dump())
    db.add(inspection); db.flush()
    db.add(AuditEvent(organization_id=project.organization_id, subject_id=subject,
                      action="inspection.create", resource_id=inspection.id))
    db.commit()
    return {"id":inspection.id}

@router.get("/projects/{project_id}/inspections")
def inspections(project_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    access(db, subject, project_id, ["OWNER","ADMIN","ENGINEER","INSPECTOR","FIELD_OPERATOR","VIEWER"])
    rows = db.scalars(select(Inspection).where(Inspection.project_id == project_id)).all()
    return [{"id":i.id,"description":i.description,"status":i.status} for i in rows]
