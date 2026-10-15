"""Portfolio, weekly schedule, contracts and the Tuntum import, against an isolated database."""
import json
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Expense, Payment, Project
from app.security import require_identity
from scripts import import_tuntum


@pytest.fixture()
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    data = json.loads(import_tuntum.DATA.read_text(encoding="utf-8"))
    with Session(engine) as db:
        report = import_tuntum.run(db, "Grupo MG", "owner", "import:test", data)
        db.commit()

    def get_test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[require_identity] = lambda: "owner"
    try:
        yield TestClient(app), engine, data, report
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_import_matches_source_and_is_idempotent(env):
    client, engine, data, report = env
    assert report.created["project"] == len(data["locations"]) + 1  # + cost pool for shared expenses
    with Session(engine) as db:
        scheduled = db.scalar(select(func.sum(Payment.amount)).where(Payment.status == "SCHEDULED"))
        assert scheduled == Decimal("31570.87")  # FOPAG 28/08/2026 total
        assert db.scalar(select(func.count(Payment.id)).where(Payment.status == "PAID")) == 0  # nothing presumed paid
        assert db.scalar(select(func.count(Project.id)).where(Project.budget.is_not(None))) == 0  # never invented
        again = import_tuntum.run(db, "Grupo MG", "owner", "import:test", data)
        assert again.created == {} and db.scalar(select(func.count(Expense.id))) == 16
    # The PDF TOTAL row uses inconsistent ranges; the importer reports it instead of hiding it.
    assert any("contracts_total" in line for line in report.divergences)


def test_supplier_debt_is_not_double_counted(env):
    client, engine, data, _ = env
    with Session(engine) as db:
        marcelo = db.scalars(select(Expense).where(Expense.supplier == "Marcelo Construções")).all()
        assert len(marcelo) == 1 and marcelo[0].amount == Decimal("24670.00")
        payments = db.scalars(select(Payment).where(Payment.expense_id == marcelo[0].id)).all()
        assert [p.amount for p in payments] == [Decimal("5000.00")]


def test_portfolio_totals_and_progress_without_measurements(env):
    client, *_ = env
    body = client.get("/api/v1/portfolio").json()
    assert body["totals"]["scheduled_total"] == "31570.87"
    assert body["totals"]["paid_total"] == "0.00"
    assert body["totals"]["contracts_total"] == "736169.72"
    assert body["totals"]["measured_projects"] == 0
    assert all(p["physical"] is None for p in body["projects"])  # no progress inferred from money
    pool = [p for p in body["projects"] if p["status"] == "COST_POOL"]
    assert len(pool) == 1 and pool[0]["scheduled_total"] == "5985.87"


def test_schedule_window_and_validation(env):
    client, *_ = env
    week = client.get("/api/v1/schedule", params={"start": "2026-08-24", "end": "2026-08-30"}).json()
    assert len(week["items"]) == 16 and week["latest"] == "2026-08-28"
    assert client.get("/api/v1/schedule", params={"start": "2026-09-01", "end": "2026-09-07"}).json()["items"] == []
    assert client.get("/api/v1/schedule", params={"start": "2026-08-30", "end": "2026-08-01"}).status_code == 422
    default = client.get("/api/v1/schedule").json()  # latest week with payments (Mon-Sun)
    assert (default["start"], default["end"], len(default["items"])) == ("2026-08-24", "2026-08-30", 16)
    assert client.get("/api/v1/schedule", params={"start": "2026-08-24"}).status_code == 422
    assert client.get("/api/v1/schedule", params={"start": "2026-01-01", "end": "2026-12-31"}).status_code == 422


def test_other_tenant_sees_nothing_and_cannot_edit(env):
    client, engine, *_ = env
    with Session(engine) as db:
        pid = db.scalar(select(Project.id).where(Project.name == "MG Tabocal"))
    app.dependency_overrides[require_identity] = lambda: "intruso"
    assert client.get("/api/v1/portfolio").json() == {"projects": [], "totals": {}}
    assert client.get("/api/v1/contracts").json() == []
    assert client.patch(f"/api/v1/projects/{pid}", json={"municipality": "X"}).status_code == 404


def test_update_project_details_and_coordinates(env):
    client, engine, *_ = env
    with Session(engine) as db:
        pid = db.scalar(select(Project.id).where(Project.name == "MG Tabocal"))
    assert client.patch(f"/api/v1/projects/{pid}", json={"latitude": -5.25}).status_code == 422  # both or none
    assert client.patch(f"/api/v1/projects/{pid}", json={"latitude": -95, "longitude": -44.6}).status_code == 422
    assert client.patch(f"/api/v1/projects/{pid}", json={"status": "FINISHED"}).status_code == 422
    ok = client.patch(f"/api/v1/projects/{pid}", json={"address": "Zona rural", "status": "PAUSED", "budget": "120000"})
    assert ok.status_code == 200 and ok.json()["updated"] == ["address", "budget", "status"]
    row = next(p for p in client.get("/api/v1/portfolio").json()["projects"] if p["id"] == pid)
    assert row["status"] == "PAUSED" and row["budget"] == "120000.00"


def test_payables_show_outstanding_debts(env):
    client, *_ = env
    rows = client.get("/api/v1/payables").json()
    marcelo = next(row for row in rows if row["supplier"] == "Marcelo Construções")
    assert (marcelo["amount"], marcelo["scheduled"], marcelo["paid"], marcelo["outstanding"]) ==         ("24670.00", "5000.00", "0.00", "24670.00")
    portfolio = client.get("/api/v1/portfolio").json()
    assert portfolio["totals"]["open_total"] == "56965.37"
    tabocal = next(p for p in portfolio["projects"] if p["name"] == "MG Tabocal")
    assert tabocal["latest_report"]["summary"].startswith("Relato do contratante")


def test_advance_ratio_ignores_contracts_without_total(env):
    client, *_ = env
    casa = next(p for p in client.get("/api/v1/portfolio").json()["projects"] if p["name"] == "Casa BDC / Casa Barra")
    c = casa["contracts"]
    assert c["count"] == 4 and c["reported_advance"] == "33490.00" and c["advance_on_valued"] == "24490.00"
    assert Decimal(c["advance_on_valued"]) <= Decimal(c["total"])


def test_project_details_roundtrip(env):
    client, engine, *_ = env
    with Session(engine) as db:
        pid = db.scalar(select(Project.id).where(Project.name == "MG Cipó"))
    assert client.patch(f"/api/v1/projects/{pid}", json={"latitude": "-5.2591", "longitude": "-44.6489",
                                                         "start_date": "2026-08-01", "end_date": "2026-07-01"}).status_code == 422
    assert client.patch(f"/api/v1/projects/{pid}", json={"latitude": "-5.2591", "longitude": "-44.6489"}).status_code == 200
    details = client.get(f"/api/v1/projects/{pid}/details").json()
    assert (details["latitude"], details["longitude"], details["budget"]) == ("-5.259100", "-44.648900", None)
    app.dependency_overrides[require_identity] = lambda: "intruso"
    assert client.get(f"/api/v1/projects/{pid}/details").status_code == 404
