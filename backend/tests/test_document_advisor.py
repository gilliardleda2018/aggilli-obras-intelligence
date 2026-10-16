"""Document advisor: provenance, missing fields, no writes, isolation."""
from types import SimpleNamespace as Row
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db import Base, get_db
from app.main import app
from app.models import FieldDocument, Membership, Organization
from app.security import require_identity
from app.document_advisor import assess


def document(**overrides):
    values = dict(id="d1", sha256="a"*64, status="PENDING", extraction=None,
                  extraction_error=None, extraction_engine=None, project_id=None,
                  suggested_project_id=None, suggestion_reason="Sem localização", expense_id=None)
    values.update(overrides)
    return Row(**values)


def test_missing_ocr_is_not_fabricated():
    result = assess(document())
    codes = [f["code"] for f in result["findings"]]
    assert "OCR_NOT_AVAILABLE" in codes
    assert "AMOUNT_MISSING" in codes and "SUPPLIER_MISSING" in codes
    assert result["source_sha256"] == "a"*64


def test_ocr_problems_require_human_review():
    result = assess(document(extraction='{"fields":{"supplier_name":"ABC","total_amount":"100.00"},"problems":["chave inválida"]}',
                             project_id="p1"))
    assert [f["code"] for f in result["findings"]] == ["OCR_REVIEW_REQUIRED"]


def test_document_isolation_and_no_writes():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        a, b = Organization(name="A"), Organization(name="B")
        db.add_all([a,b]); db.flush()
        db.add_all([Membership(organization_id=a.id, subject_id="owner", role="OWNER"),
                    Membership(organization_id=b.id, subject_id="other", role="OWNER")])
        for org, sha in ((a, "a"*64), (b, "b"*64)):
            db.add(FieldDocument(organization_id=org.id, sha256=sha, status="PENDING", storage_key="x",
                                 content_type="image/jpeg", size_bytes=12, width=2, height=2,
                                 recorded_by="owner", created_at=datetime.now(timezone.utc)))
        db.commit()
    def test_db():
        with Session(engine) as db:
            yield db
    who = {"sub":"owner"}
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[require_identity] = lambda:who["sub"]
    try:
        client=TestClient(app)
        res=client.get("/api/v1/document-auditor/diagnosis")
        assert res.status_code==200
        body=res.json()
        assert len(body["documents"])==1 and body["documents"][0]["source_sha256"]=="a"*64
        assert body["writes_performed"] is False
        who["sub"]="outsider"
        assert client.get("/api/v1/document-auditor/diagnosis").json()["documents"]==[]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
