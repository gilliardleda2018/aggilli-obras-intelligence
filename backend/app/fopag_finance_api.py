"""Authenticated read-only reconciliation of FOPAG contracts for a project.

No Stripe integration or write operations. Finance scheduling/confirmation remain
the existing operations endpoints and require separate evidence.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import LaborContract
from .measurements import access
from .security import require_identity
from .fopag_reconciliation import reconcile_contracts

router = APIRouter(prefix="/api/v1", tags=["fopag-finance"])


@router.get("/projects/{project_id}/fopag/reconciliation")
def project_fopag_reconciliation(project_id: str, subject: str = Depends(require_identity),
                                 db: Session = Depends(get_db)):
    access(db, subject, project_id, ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "VIEWER"])
    rows = db.scalars(select(LaborContract).where(LaborContract.project_id == project_id)
                      .order_by(LaborContract.source_ref, LaborContract.id)).all()
    return reconcile_contracts([
        {"name": c.contractor, "project": project_id, "total": c.total,
         "advance": c.reported_advance, "balance": c.reported_balance}
        for c in rows
    ])
