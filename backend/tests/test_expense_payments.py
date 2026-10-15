from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db import Base,get_db
from app.main import app
from app.models import Organization,Membership,Project,Expense,Payment
from app.security import require_identity

def test_expense_schedule_confirm_and_tenant_isolation():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        a=Organization(name="A"); b=Organization(name="B")
        db.add_all([a,b]);db.flush()
        db.add_all([Membership(organization_id=a.id,subject_id="owner",role="OWNER"),
                    Membership(organization_id=b.id,subject_id="outsider",role="OWNER"),
                    Membership(organization_id=a.id,subject_id="field",role="FIELD_OPERATOR")])
        project=Project(organization_id=a.id,name="Obra",location="Tuntum",budget=Decimal("10000"),
                        start_date=date(2026,1,1),end_date=date(2026,12,31))
        db.add(project);db.commit();pid=project.id
    def test_db():
        with Session(engine) as db: yield db
    app.dependency_overrides[get_db]=test_db
    app.dependency_overrides[require_identity]=lambda:"outsider"
    try:
        client=TestClient(app)
        payload={"description":"Cimento","supplier":"Darlan","amount":"935.00","category":"MATERIAL"}
        assert client.post(f"/api/v1/projects/{pid}/expenses",json=payload).status_code==404
        app.dependency_overrides[require_identity]=lambda:"field"
        response=client.post(f"/api/v1/projects/{pid}/expenses",json=payload)
        assert response.status_code==201,response.text
        eid=response.json()["id"]
        assert client.post(f"/api/v1/expenses/{eid}/payments",json={
            "amount":"935","scheduled_date":"2026-10-16"}).status_code==404
        app.dependency_overrides[require_identity]=lambda:"owner"
        response=client.post(f"/api/v1/expenses/{eid}/payments",json={
            "amount":"935","scheduled_date":"2026-10-16"})
        assert response.status_code==201,response.text
        payment=response.json()["id"]
        assert client.post(f"/api/v1/expenses/{eid}/payments",json={
            "amount":"1","scheduled_date":"2026-10-16"}).status_code==409
        assert client.post(f"/api/v1/payments/{payment}/confirm",json={"reference":"BANK-123"}).status_code==200
        assert client.post(f"/api/v1/payments/{payment}/confirm",json={"reference":"BANK-123"}).status_code==409
        assert client.get(f"/api/v1/projects/{pid}/payments").json()[0]["status"]=="PAID"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
