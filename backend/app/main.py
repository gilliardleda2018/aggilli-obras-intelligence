from datetime import date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Aggilli Obras Intelligence", version="0.1.0")

class Stage(BaseModel):
    name: str
    weight: float = Field(ge=0, le=100)
    progress: float = Field(ge=0, le=100)

class Project(BaseModel):
    id: int
    name: str
    location: str
    budget: float = Field(ge=0)
    start_date: date
    end_date: date
    stages: list[Stage]

DEMO = Project(
    id=1, name="Obra demonstrativa", location="Brasil", budget=2500000,
    start_date=date(2026, 1, 1), end_date=date(2027, 1, 1),
    stages=[
        Stage(name="Fundação", weight=20, progress=100),
        Stage(name="Estrutura", weight=30, progress=80),
        Stage(name="Alvenaria", weight=25, progress=60),
        Stage(name="Instalações", weight=15, progress=40),
        Stage(name="Acabamento", weight=10, progress=10),
    ],
)

def physical_progress(stages: list[Stage]) -> float:
    total = sum(s.weight for s in stages)
    if abs(total - 100) > 1e-6:
        raise ValueError("Os pesos das etapas devem somar 100")
    return round(sum(s.weight * s.progress for s in stages) / 100, 2)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/v1/demo/project")
def demo_project():
    return {**DEMO.model_dump(mode="json"), "physical_progress": physical_progress(DEMO.stages)}

from .projects import router as projects_router
app.include_router(projects_router)

from .measurements import router as measurements_router
app.include_router(measurements_router)

from .materials import router as materials_router
from .finance import router as finance_router
app.include_router(materials_router)
app.include_router(finance_router)

from .field import router as field_router
app.include_router(field_router)

from .reports import router as reports_router
from .insights import router as insights_router
app.include_router(reports_router)
app.include_router(insights_router)

from .operations import router as operations_router
app.include_router(operations_router)

from .portfolio import router as portfolio_router
app.include_router(portfolio_router)

from .intelligence import router as intelligence_router
app.include_router(intelligence_router)

from .imports import router as imports_router
app.include_router(imports_router)

from .alerts import router as alerts_router
app.include_router(alerts_router)

from .report_export import router as report_export_router
app.include_router(report_export_router)

from .geo import router as geo_router
app.include_router(geo_router)
