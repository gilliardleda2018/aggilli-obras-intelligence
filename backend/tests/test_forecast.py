"""Forecast engine and intelligence API: honesty with little data, correct math, history, recalculation, isolation."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import forecast
from app.db import Base, get_db
from app.main import app
from app.models import Expense, ForecastRun, Measurement, Membership, Organization, Project, ServiceItem
from app.security import require_identity

START = date(2026, 6, 1)


def linear_inputs(weeks=10, per_week=5.0, budget=None, end_weeks=20, cost_per_point=1000.0):
    progress = [(START + timedelta(weeks=w), per_week * w) for w in range(1, weeks + 1)]
    costs = [(d, p * cost_per_point) for d, p in progress]
    return forecast.ProjectInputs(start_date=START, end_date=START + timedelta(weeks=end_weeks), budget=budget,
                                  progress=progress, costs=costs, planning_complete=True,
                                  services=[{"name": "A", "weight": 100.0, "progress": per_week * weeks}], today=START + timedelta(weeks=weeks))


def test_insufficient_data_never_produces_numbers():
    inputs = forecast.ProjectInputs(start_date=None, end_date=None, budget=None, progress=[(START, 10.0)], costs=[],
                                    planning_complete=False)
    schedule = forecast.schedule_forecast(inputs)
    cost = forecast.cost_forecast(inputs)
    assert schedule["status"] == "dados_insuficientes" and "finish_p50" not in schedule and schedule["missing"]
    assert cost["status"] == "dados_insuficientes" and "eac_p50" not in cost


def test_constant_productivity_finishes_on_the_line():
    result = forecast.schedule_forecast(linear_inputs())  # 50% after 10 weeks at 5 pp/week → 100% at week 20
    assert result["status"] == "ok"
    expected = START + timedelta(weeks=20)
    assert abs((date.fromisoformat(result["finish_p50"]) - expected).days) <= 7
    assert result["finish_p10"] <= result["finish_p50"] <= result["finish_p90"]
    assert result["earned_schedule"]["spi_t"] == pytest.approx(1.0, abs=0.01)
    assert result["model"] == "monte-carlo-produtividade" and result["version"]


def test_slower_pace_lowers_probability_and_delays():
    on_plan = forecast.schedule_forecast(linear_inputs(per_week=5.0))
    slow = forecast.schedule_forecast(linear_inputs(per_week=3.0))
    assert slow["probability_on_time"] < on_plan["probability_on_time"]
    assert slow["delay_days_p50"] > 0


def test_evm_formulas():
    result = forecast.cost_forecast(linear_inputs(budget=80000.0, cost_per_point=1000.0))  # spent 50k for 50% of 80k
    assert result["cpi"] == pytest.approx(0.8)
    assert result["eac_p50"] == pytest.approx(100000.0)          # BAC / CPI
    assert result["methods"]["custo_restante_no_orcamento"] == pytest.approx(90000.0)  # AC + (BAC - EV)
    assert result["eac_low"] <= result["eac_p50"] <= result["eac_high"]


def test_run_rate_without_budget():
    result = forecast.cost_forecast(linear_inputs(budget=None, cost_per_point=1000.0))
    assert result["model"] == "custo-por-avanco" and result["eac_p50"] == pytest.approx(100000.0, rel=0.01)


def test_reproducible():
    assert forecast.schedule_forecast(linear_inputs()) == forecast.schedule_forecast(linear_inputs())


@pytest.fixture()
def api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org, other = Organization(name="A"), Organization(name="B")
        db.add_all([org, other]); db.flush()
        db.add_all([Membership(organization_id=org.id, subject_id="owner", role="OWNER"),
                    Membership(organization_id=other.id, subject_id="outsider", role="OWNER")])
        project = Project(organization_id=org.id, name="Obra", location="X", budget=Decimal("100000"), start_date=START,
                          end_date=START + timedelta(weeks=20))
        db.add(project); db.flush()
        service = ServiceItem(project_id=project.id, name="Serviço", unit="m", planned_quantity=Decimal(100), weight=Decimal(100))
        db.add(service); db.flush()
        for week in range(1, 5):
            day = START + timedelta(weeks=week)
            db.add(Measurement(service_item_id=service.id, quantity=Decimal(5), status="APPROVED", recorded_by="x", measured_on=day))
            db.add(Expense(project_id=project.id, description="d", supplier="s", amount=Decimal("5000"), category="MATERIAL",
                           created_by="x", expense_date=day))
        db.commit()
        ids = project.id, service.id

    def get_test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    who = {"sub": "owner"}
    app.dependency_overrides[require_identity] = lambda: who["sub"]
    try:
        yield TestClient(app), engine, ids, who
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_api_history_and_recalculation(api):
    client, engine, (pid, sid), who = api
    first = client.get(f"/api/v1/projects/{pid}/intelligence").json()
    assert first["schedule"]["status"] == "ok" and first["cost"]["status"] == "ok"
    assert len(first["series"]["progress"]) == 4 and first["series"]["baseline"]
    client.get(f"/api/v1/projects/{pid}/intelligence")
    with Session(engine) as db:
        assert db.scalar(select(func.count(ForecastRun.id))) == 2  # same inputs → no duplicate runs
        db.add(Measurement(service_item_id=sid, quantity=Decimal(10), status="APPROVED", recorded_by="x",
                           measured_on=START + timedelta(weeks=5)))
        db.commit()
    second = client.get(f"/api/v1/projects/{pid}/intelligence").json()
    assert second["schedule"]["current_progress"] == 30.0  # new approved measurement updates the inputs
    assert len(second["history"]) == 4  # previous forecast preserved
    who["sub"] = "outsider"
    assert client.get(f"/api/v1/projects/{pid}/intelligence").status_code == 404
    assert client.get("/api/v1/intelligence/portfolio").json()["projects"] == []
