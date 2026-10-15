"""Automatic alerts (duplicates, outliers, overdue payments, pending measurements) with human review, and weekly trends."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Expense, Measurement, Membership, Organization, Payment, Project, ServiceItem
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
                    Membership(organization_id=org.id, subject_id="viewer", role="VIEWER"),
                    Membership(organization_id=other.id, subject_id="outsider", role="OWNER")])
        project = Project(organization_id=org.id, name="Galpão", location="Tuntum/MA")
        db.add(project); db.flush()

        def expense(supplier, amount, days_ago, category="MATERIAL"):
            item = Expense(project_id=project.id, supplier=supplier, description="item", amount=Decimal(amount), category=category,
                           created_by="x", expense_date=TODAY - timedelta(days=days_ago))
            db.add(item); db.flush()
            return item
        expense("Loja Alfa", "500.00", 10)
        expense("Loja Alfa", "500.00", 8)                       # duplicate of the previous (same supplier, amount, 2 days)
        for i, value in enumerate(["100", "110", "95", "105", "102"]):
            expense("Depósito Beta", value, 30 + i * 7)
        expense("Depósito Beta", "2500", 3)                      # outlier for this supplier
        late = expense("Empreiteiro Gama", "1500.00", 20, "LABOR")
        db.add(Payment(expense_id=late.id, amount=Decimal("1500.00"), scheduled_date=TODAY - timedelta(days=12), created_by="x"))
        service = ServiceItem(project_id=project.id, name="Estrutura", unit="t", planned_quantity=Decimal(10), weight=Decimal(100))
        db.add(service); db.flush()
        db.add(Measurement(service_item_id=service.id, quantity=Decimal(1), status="PENDING", recorded_by="x",
                           measured_on=TODAY - timedelta(days=15)))
        db.commit()

    def get_test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    who = {"sub": "eng"}
    app.dependency_overrides[require_identity] = lambda: who["sub"]
    try:
        yield TestClient(app), who
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_detects_expected_signals_with_evidence(env):
    client, _ = env
    alerts = client.get("/api/v1/alerts").json()["alerts"]
    types = sorted(a["type"] for a in alerts)
    assert types == ["medicao_parada", "pagamento_vencido", "possivel_duplicidade", "sem_medicao_recente", "valor_incomum"]
    duplicate = next(a for a in alerts if a["type"] == "possivel_duplicidade")
    assert duplicate["severity"] == "high" and len(duplicate["evidence"]) == 2
    outlier = next(a for a in alerts if a["type"] == "valor_incomum")
    assert "Depósito Beta" in outlier["title"]


def test_review_hides_alert_and_feeds_statistics(env):
    client, who = env
    alert = next(a for a in client.get("/api/v1/alerts").json()["alerts"] if a["type"] == "valor_incomum")
    who["sub"] = "viewer"
    assert client.post(f"/api/v1/alerts/{alert['key']}/review", json={"decision": "FALSE_ALARM"}).status_code == 404
    who["sub"] = "eng"
    assert client.post(f"/api/v1/alerts/{alert['key']}/review", json={"decision": "MAYBE"}).status_code == 422
    assert client.post(f"/api/v1/alerts/{alert['key']}/review", json={"decision": "FALSE_ALARM", "note": "compra grande prevista"}).status_code == 200
    body = client.get("/api/v1/alerts").json()
    assert all(a["key"] != alert["key"] for a in body["alerts"])
    assert body["feedback"]["valor_incomum"]["false_alarm"] == 1
    reviewed = client.get("/api/v1/alerts", params={"include_reviewed": True}).json()["alerts"]
    assert next(a for a in reviewed if a["key"] == alert["key"])["review"]["note"] == "compra grande prevista"


def test_trends_and_isolation(env):
    client, who = env
    weeks = client.get("/api/v1/trends", params={"weeks": 8}).json()["weeks"]
    assert len(weeks) == 8 and sum(float(w["incurred_total"]) for w in weeks) > 0
    who["sub"] = "outsider"
    assert client.get("/api/v1/alerts").json()["alerts"] == []
    assert all(w["incurred_total"] == "0" for w in client.get("/api/v1/trends").json()["weeks"])
