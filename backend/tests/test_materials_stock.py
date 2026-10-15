"""Materials: moving average cost, purchase as expense, consumption vs. progress, coverage and alerts."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Expense, Measurement, Membership, Organization, Project, ServiceItem
from app.security import require_identity

TODAY = date.today()


@pytest.fixture()
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org, other = Organization(name="A"), Organization(name="B")
        db.add_all([org, other]); db.flush()
        db.add_all([Membership(organization_id=org.id, subject_id="eng", role="ENGINEER"),
                    Membership(organization_id=org.id, subject_id="field", role="FIELD_OPERATOR"),
                    Membership(organization_id=other.id, subject_id="outsider", role="OWNER")])
        project = Project(organization_id=org.id, name="Galpão", location="X")
        db.add(project); db.flush()
        service = ServiceItem(project_id=project.id, name="Concreto", unit="m³", planned_quantity=Decimal(100), weight=Decimal(100))
        db.add(service); db.flush()
        db.add(Measurement(service_item_id=service.id, quantity=Decimal(20), status="APPROVED", recorded_by="x", measured_on=TODAY))
        db.commit()
        ids = project.id, service.id

    def get_test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    who = {"sub": "eng"}
    app.dependency_overrides[require_identity] = lambda: who["sub"]
    try:
        yield TestClient(app), engine, ids, who
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_stock_cost_consumption_and_alerts(env):
    client, engine, (pid, sid), who = env
    created = client.post(f"/api/v1/projects/{pid}/materials", json={"name": "Cimento CP-II", "unit": "saco", "category": "Cimento",
                                                                    "min_stock": "40", "planned_quantity": "500", "service_id": sid})
    assert created.status_code == 201, created.text
    mid = created.json()["id"]
    days = lambda n: (TODAY - timedelta(days=n)).isoformat()  # noqa: E731
    entry = client.post(f"/api/v1/materials/{mid}/movements", json={"kind": "IN", "quantity": "100", "unit_cost": "30", "supplier": "Marcelo",
                                                                    "movement_date": days(20), "create_expense": True})
    assert entry.status_code == 201 and entry.json()["expense_id"]
    client.post(f"/api/v1/materials/{mid}/movements", json={"kind": "IN", "quantity": "100", "unit_cost": "36", "movement_date": days(15)})
    who["sub"] = "field"
    assert client.post(f"/api/v1/materials/{mid}/movements", json={"kind": "OUT", "quantity": "150", "movement_date": days(5),
                                                                   "note": "laje"}).status_code == 201
    assert client.post(f"/api/v1/materials/{mid}/movements", json={"kind": "OUT", "quantity": "999"}).status_code == 409
    assert client.post(f"/api/v1/materials/{mid}/movements", json={"kind": "OUT", "quantity": "1",
                                                                   "movement_date": (TODAY + timedelta(days=2)).isoformat()}).status_code == 422
    row = client.get(f"/api/v1/projects/{pid}/materials").json()[0]
    assert row["balance"] == "50.000" and row["avg_cost"] == "33.0000" and row["stock_value"] == "1650.00"
    assert row["expected_consumption"] == "100.000"  # 500 planned × 20% measured progress
    assert row["flags"] == ["consumo_acima"] and row["coverage_days"] == 10  # 150 used > 115 tolerated; 50 left at 5/day
    with Session(engine) as db:
        assert db.scalar(select(func.sum(Expense.amount))) == Decimal("3000.00")  # only the entry flagged as a new purchase
    who["sub"] = "eng"
    types = {a["type"] for a in client.get("/api/v1/alerts").json()["alerts"]}
    assert "consumo_acima" in types and "ruptura_proxima" not in types
    overview = client.get("/api/v1/materials/overview").json()
    assert overview["stock_value"] == "1650.00" and overview["flagged"] == 1
    assert len(client.get(f"/api/v1/materials/{mid}/movements").json()) == 3


def test_validation_and_isolation(env):
    client, _, (pid, sid), who = env
    mid = client.post(f"/api/v1/projects/{pid}/materials", json={"name": "Areia", "unit": "m³"}).json()["id"]
    assert client.post(f"/api/v1/materials/{mid}/movements", json={"kind": "IN", "quantity": "5", "create_expense": True}).status_code == 422
    assert client.patch(f"/api/v1/materials/{mid}", json={"min_stock": "3"}).json()["updated"] == ["min_stock"]
    who["sub"] = "outsider"
    assert client.get(f"/api/v1/projects/{pid}/materials").status_code == 404
    assert client.get("/api/v1/materials/overview").json()["materials"] == []
    assert client.post(f"/api/v1/materials/{mid}/movements", json={"kind": "IN", "quantity": "1"}).status_code == 404
