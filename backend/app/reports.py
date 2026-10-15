import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from .db import get_db
from .measurements import dashboard, access
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["reports"])

@router.get("/projects/{project_id}/reports/progress.csv")
def progress_csv(project_id: str, subject: str = Depends(require_identity),
                 db: Session = Depends(get_db)):
    # Reuse the same tenant-checked data aggregation as the dashboard.
    data = dashboard(project_id, subject, db)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Serviço","Unidade","Quantidade prevista","Quantidade aprovada","Peso (%)","Avanço (%)"])
    for item in data["stages"]:
        writer.writerow([item["name"],item["unit"],item["planned_quantity"],
                         item["approved_quantity"],item["weight"],item["progress"]])
    writer.writerow(["AVANÇO TOTAL","","","","",data["physical_progress"]])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition":'attachment; filename="progresso.csv"'})
