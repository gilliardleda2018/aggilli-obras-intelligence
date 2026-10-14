from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.main import app
from app.security import require_identity
from app.models import Organization, Membership, Project
from datetime import date

def test_organization_isolation_and_approval():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        a=Organization(name="A"); b=Organization(name="B")
        db.add_all([a,b]);db.flush()
        db.add_all([Membership(organization_id=a.id,subject_id="owner",role="OWNER"),
                    Membership(organization_id=b.id,subject_id="other",role="OWNER")])
        project=Project(organization_id=a.id,name="Obra A",location="BR",budget=Decimal("100"),
                        start_date=date(2026,1,1),end_date=date(2026,12,31))
        db.add(project);db.commit(); pid=project.id
    def session_override():
        with Session(engine) as db: yield db
    app.dependency_overrides[get_db]=session_override
    app.dependency_overrides[require_identity]=lambda:"other"
    try:
        client=TestClient(app)
        assert client.get("/api/v1/projects/"+pid+"/dashboard").status_code==404
        assert client.post("/api/v1/projects/"+pid+"/services",json={
            "name":"Concreto","unit":"m3","planned_quantity":"10","weight":"100"}).status_code==404
        app.dependency_overrides[require_identity]=lambda:"owner"
        r=client.post("/api/v1/projects/"+pid+"/services",json={
            "name":"Concreto","unit":"m3","planned_quantity":"10","weight":"100"})
        assert r.status_code==201,r.text
        sid=r.json()["id"]
        r=client.post("/api/v1/services/"+sid+"/measurements",json={"quantity":"4"})
        assert r.status_code==201,r.text
        mid=r.json()["id"]
        assert client.post("/api/v1/measurements/"+mid+"/approve").status_code==200
        assert client.post("/api/v1/measurements/"+mid+"/approve").status_code==409
        d=client.get("/api/v1/projects/"+pid+"/dashboard").json()
        assert d["physical_progress"]==40.0
        r=client.post("/api/v1/services/"+sid+"/measurements",json={"quantity":"7"})
        assert client.post("/api/v1/measurements/"+r.json()["id"]+"/approve").status_code==409
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
