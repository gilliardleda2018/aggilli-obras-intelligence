from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .db import get_db
from .measurements import dashboard
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["insights"])

@router.get("/projects/{project_id}/insights")
def project_insights(project_id: str, subject: str = Depends(require_identity),
                     db: Session = Depends(get_db)):
    data = dashboard(project_id, subject, db)
    alerts = []
    if not data["planning_complete"]:
        alerts.append({"code":"INCOMPLETE_PLAN","severity":"warning",
                       "message":"Pesos dos serviços ainda não totalizam 100%."})
    if not data["stages"]:
        alerts.append({"code":"NO_SERVICES","severity":"warning",
                       "message":"Cadastre serviços para acompanhar o avanço físico."})
    return {"project_id":project_id,"physical_progress":data["physical_progress"],
            "alerts":alerts,"forecast":None,
            "note":"Regras determinísticas; previsão por IA ainda não habilitada."}
