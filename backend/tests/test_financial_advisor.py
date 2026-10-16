"""Financial advisor: real source arithmetic, payment semantics, tenant isolation."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace as Row
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.main import app
from app.models import Organization, Membership, Project, LaborContract, Expense, Payment
from app.security import require_identity
from app.financial_advisor import diagnose


def test_contract_balance_is_preserved_and_flagged():
    c = Row(id="c1", project_id="p1", total=Decimal("60000.00"),
            reported_advance=Decimal("9300.00"), reported_balance=Decimal("4500.00"), source_ref="original")
    findings = diagnose([c], [], [], date(2026, 10, 16))
    assert len(findings) == 1
    assert findings[0]["code"] == "CONTRACT_BALANCE_DIVERGENCE"
    assert findings[0]["evidence"]["calculated_balance"] == "50700.00"
    assert findings[0]["evidence"]["reported_balance"] == "4500.00"
    assert c.reported_balance == Decimal("4500.00")


def test_scheduled_is_never_paid_and_overdue_requires_review():
    e = Row(id="e1", project_id="p1", amount=Decimal("100.00"))
    p = Row(expense_id="e1", amount=Decimal("100.00"), status="SCHEDULED",
            scheduled_date=date(2026, 8, 28))
    result = diagnose([], [e], [p], date(2026, 10, 16))
    assert [f["code"] for f in result] == ["SCHEDULED_OVERDUE"]
    assert p.status == "SCHEDULED"


def test_tenant_scope_and_no_database_writes():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        a, b = Organization(name="A"), Organization(name="B")
        db.add_all([a, b]); db.flush()
        db.add_all([Membership(organization_id=a.id, subject_id="owner", role="OWNER"),
                    Membership(organization_id=b.id, subject_id="other", role="OWNER")])
        p1, p2 = Project(organization_id=a.id, name="A", location="A"), Project(organization_id=b.id, name="B", location="B")
        db.add_all([p1, p2]); db.flush()
        db.add_all([LaborContract(project_id=p1.id, contractor="A", total=Decimal(100),
                                   reported_advance=Decimal(20), reported_balance=Decimal(10), created_by="owner"),
                    LaborContract(project_id=p2.id, contractor="B", total=Decimal(100),
                                   reported_advance=Decimal(20), reported_balance=Decimal(10), created_by="other")])
        db.commit()
    def get_test_db():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = get_test_db
    who = {"sub": "owner"}
    app.dependency_overrides[require_identity] = lambda: who["sub"]
    try:
        client = TestClient(app)
        result = client.get("/api/v1/finance-agent/diagnosis")
        assert result.status_code == 200
        body = result.json()
        assert body["projects"] == 1 and body["writes_performed"] is False
        assert len(body["findings"]) == 1
        with Session(engine) as db:
            assert len(db.scalars(select(LaborContract)).all()) == 2
        who["sub"] = "outsider"
        assert client.get("/api/v1/finance-agent/diagnosis").json()["findings"] == []
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
