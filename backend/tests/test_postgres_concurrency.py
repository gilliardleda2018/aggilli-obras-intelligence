"""PostgreSQL-only integration tests; requires migrated DATABASE_URL."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Organization, Membership, Project, ServiceItem, Measurement, Material, StockMovement
from app.measurements import approve_measurement
from app.materials import movement, MovementCreate
from fastapi import HTTPException

pytestmark=pytest.mark.skipif(not os.getenv("DATABASE_URL","").startswith("postgresql"),
                              reason="PostgreSQL integration only")

@pytest.fixture
def seeded():
    engine=create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as db:
        org=Organization(name="Concurrency test")
        db.add(org);db.flush()
        db.add(Membership(organization_id=org.id,subject_id="test-owner",role="OWNER"))
        project=Project(organization_id=org.id,name="Test",location="BR",budget=Decimal(100),
                        start_date=date(2026,1,1),end_date=date(2026,12,31))
        db.add(project);db.flush()
        service=ServiceItem(project_id=project.id,name="Concrete",unit="m3",
                            planned_quantity=Decimal(10),weight=Decimal(100))
        material=Material(project_id=project.id,name="Cement",unit="bag")
        db.add_all([service,material]);db.flush()
        m1=Measurement(service_item_id=service.id,quantity=Decimal(7),recorded_by="test-owner")
        m2=Measurement(service_item_id=service.id,quantity=Decimal(7),recorded_by="test-owner")
        db.add_all([m1,m2,StockMovement(material_id=material.id,kind="IN",
                                        quantity=Decimal(10),recorded_by="test-owner")])
        db.commit()
        ids=(m1.id,m2.id,material.id,service.id,org.id)
    yield engine,ids
    with Session(engine) as db:
        from app.models import AuditEvent
        db.query(AuditEvent).filter(AuditEvent.organization_id==ids[4]).delete()
        db.query(Measurement).filter(Measurement.service_item_id==ids[3]).delete()
        db.query(StockMovement).filter(StockMovement.material_id==ids[2]).delete()
        db.query(Material).filter(Material.id==ids[2]).delete()
        db.query(ServiceItem).filter(ServiceItem.id==ids[3]).delete()
        project_ids=[p.id for p in db.query(Project).filter(Project.organization_id==ids[4]).all()]
        db.query(Project).filter(Project.id.in_(project_ids)).delete(synchronize_session=False)
        db.query(Membership).filter(Membership.organization_id==ids[4]).delete()
        db.query(Organization).filter(Organization.id==ids[4]).delete()
        db.commit()
    engine.dispose()

def test_approval_serialization(seeded):
    engine,(m1,m2,material,service,org)=seeded
    def run(mid):
        with Session(engine) as db:
            try: return approve_measurement(mid,"test-owner",db)["status"]
            except HTTPException as exc: return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(run,[m1,m2]))
    assert sorted(map(str,results))==["409","APPROVED"]

def test_stock_serialization(seeded):
    engine,(_,_,material,_,_)=seeded
    def run(_):
        with Session(engine) as db:
            try: return movement(material,MovementCreate(quantity=Decimal(7),kind="OUT"),"test-owner",db)["balance"]
            except HTTPException as exc: return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(run,[1,2]))
    assert len([x for x in results if x==409])==1
