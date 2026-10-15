"""Measurement workflow: services list, record with date/notes, approve/reject with trail, pending queue."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import AuditEvent, Membership, Organization, Project
from app.security import require_identity


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org, other = Organization(name="A"), Organization(name="B")
        db.add_all([org, other]); db.flush()
        db.add_all([Membership(organization_id=org.id, subject_id="eng", role="ENGINEER"),
                    Membership(organization_id=org.id, subject_id="field", role="FIELD_OPERATOR"),
                    Membership(organization_id=org.id, subject_id="viewer", role="VIEWER"),
                    Membership(organization_id=other.id, subject_id="outsider", role="OWNER")])
        project = Project(organization_id=org.id, name="Galpão", location="Tuntum/MA")
        db.add(project); db.commit()
        pid = project.id

    def get_test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    who = {"sub": "eng"}
    app.dependency_overrides[require_identity] = lambda: who["sub"]
    try:
        yield TestClient(app), pid, who, engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_full_review_cycle(client):
    http, pid, who, engine = client
    service = http.post(f"/api/v1/projects/{pid}/services", json={"name": "Estrutura metálica", "unit": "t",
                                                                  "planned_quantity": "10", "weight": "60"}).json()["id"]
    listing = http.get(f"/api/v1/projects/{pid}/services").json()
    assert (listing["weight_total"], listing["weight_available"]) == ("60.0000", "40.0000")

    who["sub"] = "field"
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert http.post(f"/api/v1/services/{service}/measurements", json={"quantity": "2", "measured_on": tomorrow}).status_code == 422
    first = http.post(f"/api/v1/services/{service}/measurements",
                      json={"quantity": "4", "measured_on": "2026-10-10", "notes": "Pilares do eixo A"}).json()["id"]
    second = http.post(f"/api/v1/services/{service}/measurements", json={"quantity": "3"}).json()["id"]
    assert http.post(f"/api/v1/measurements/{first}/approve").status_code == 404  # field operator cannot approve

    who["sub"] = "eng"
    assert [row["id"] for row in http.get("/api/v1/measurements/pending").json()] == [first, second]
    assert http.post(f"/api/v1/measurements/{first}/approve").status_code == 200
    assert http.post(f"/api/v1/measurements/{second}/reject", json={"reason": "x"}).status_code == 422  # reason required
    assert http.post(f"/api/v1/measurements/{second}/reject", json={"reason": "Quantidade não confere com o croqui"}).status_code == 200
    assert http.post(f"/api/v1/measurements/{second}/approve").status_code == 409

    rows = {row["id"]: row for row in http.get(f"/api/v1/projects/{pid}/measurements").json()}
    assert rows[first]["status"] == "APPROVED" and rows[first]["decided_by"] == "eng" and rows[first]["measured_on"] == "2026-10-10"
    assert rows[second]["status"] == "REJECTED" and rows[second]["decision_reason"].startswith("Quantidade")
    service_row = http.get(f"/api/v1/projects/{pid}/services").json()["services"][0]
    assert (service_row["approved_quantity"], service_row["remaining_quantity"], service_row["progress"]) == ("4.000", "6.000", 40.0)
    assert http.get(f"/api/v1/projects/{pid}/dashboard").json()["physical_progress"] == 40.0  # 60% weight, 40% done → 40% of planned
    with Session(engine) as db:
        actions = {a.action for a in db.scalars(select(AuditEvent)).all()}
    assert {"service.create", "measurement.record", "measurement.approve", "measurement.reject"} <= actions


def test_viewer_and_other_tenant(client):
    http, pid, who, _ = client
    who["sub"] = "viewer"
    assert http.get(f"/api/v1/projects/{pid}/services").status_code == 200
    assert http.post(f"/api/v1/projects/{pid}/services", json={"name": "X", "unit": "m", "planned_quantity": "1",
                                                               "weight": "10"}).status_code == 404
    who["sub"] = "outsider"
    assert http.get(f"/api/v1/projects/{pid}/measurements").status_code == 404
    assert http.get("/api/v1/measurements/pending").json() == []
