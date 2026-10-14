from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.main import app
from app.security import require_identity
from app.models import Organization, Membership, Project

def test_stock_and_costs_are_tenant_scoped():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        a=Organization(name="A"); b=Organization(name="B")
        db.add_all([a,b]);db.flush()
        db.add_all([Membership(organization_id=a.id,subject_id="owner",role="OWNER"),
                    Membership(organization_id=b.id,subject_id="outsider",role="OWNER")])
        p=Project(organization_id=a.id,name="Obra",location="BR",budget=Decimal("1000"),
                  start_date=date(2026,1,1),end_date=date(2026,12,31))
        db.add(p);db.commit(); pid=p.id
    def get_test_db():
        with Session(engine) as session: yield session
    app.dependency_overrides[get_db]=get_test_db
    app.dependency_overrides[require_identity]=lambda:"outsider"
    try:
        client=TestClient(app)
        assert client.post(f"/api/v1/projects/{pid}/materials",json={"name":"Cimento","unit":"saco"}).status_code==404
        assert client.post(f"/api/v1/projects/{pid}/costs",json={"description":"Compra","amount":"25"}).status_code==404
        app.dependency_overrides[require_identity]=lambda:"owner"
        result=client.post(f"/api/v1/projects/{pid}/materials",json={"name":"Cimento","unit":"saco"})
        assert result.status_code==201,result.text
        mid=result.json()["id"]
        assert client.post(f"/api/v1/materials/{mid}/movements",json={"kind":"OUT","quantity":"1"}).status_code==409
        assert client.post(f"/api/v1/materials/{mid}/movements",json={"kind":"IN","quantity":"5"}).status_code==201
        assert client.post(f"/api/v1/materials/{mid}/movements",json={"kind":"OUT","quantity":"2"}).json()["balance"]=="3.000"
        assert client.post(f"/api/v1/projects/{pid}/costs",json={"description":"Compra","amount":"25"}).status_code==201
        assert Decimal(client.get(f"/api/v1/projects/{pid}/finance").json()["remaining"])==Decimal("975")
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
