"""Field documents: NF-e key check digit, work suggested by GPS, OCR as suggestion only, confirmation into expenses."""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import ocr
from app.db import Base, get_db
from app.main import app
from app.models import Expense, FieldDocument, Membership, Organization, Payment, Project
from app.security import require_identity
from tests.test_diary import jpeg

SCHOOL = (-5.258123, -44.648988)
CLINIC = (-5.300000, -44.700000)  # ~7 km away


def img(n: int, **kw) -> bytes:
    """A distinct picture per n (close colours can compress to identical files)."""
    return jpeg(((n * 37) % 256, (n * 91) % 256, (n * 53) % 256), **kw)


def key43(body: str) -> str:
    return body + str(ocr.access_key_digit(body))


# MA (21), 2026-10, CNPJ 12.345.678/0001-95, model 55, series 1, number 4321, emission 1, code 12345678
VALID_KEY = key43("21" + "2610" + "12345678000195" + "55" + "001" + "000004321" + "1" + "12345678")


def reading(**fields):
    base = {"kind": "NOTA_FISCAL", "supplier_name": "Casa do Construtor Ltda", "supplier_cnpj": "12.345.678/0001-95",
            "document_number": "4321", "access_key": VALID_KEY, "issue_date": "2026-10-14", "total_amount": 350.0,
            "items": [{"description": "Cimento CP II 50kg", "quantity": 10, "unit": "SC", "total": 350.0}],
            "payment_method": "Pix", "site_reference": None, "confidence": "high", "issues": []}
    return {**base, **fields}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOTO_STORAGE_DIR", str(tmp_path))
    monkeypatch.delenv("FILE_STORAGE_BUCKET", raising=False)
    monkeypatch.setenv("DOC_AI_PROVIDER", "off")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org, other = Organization(name="Construtora"), Organization(name="Outra")
        db.add_all([org, other]); db.flush()
        db.add_all([Membership(organization_id=org.id, subject_id="campo", role="FIELD_OPERATOR"),
                    Membership(organization_id=org.id, subject_id="viewer", role="VIEWER"),
                    Membership(organization_id=other.id, subject_id="outsider", role="OWNER")])
        school = Project(organization_id=org.id, name="Escola", location="Tuntum", latitude=Decimal(str(SCHOOL[0])), longitude=Decimal(str(SCHOOL[1])))
        clinic = Project(organization_id=org.id, name="Posto de saúde", location="Tuntum", latitude=Decimal(str(CLINIC[0])), longitude=Decimal(str(CLINIC[1])))
        foreign = Project(organization_id=other.id, name="Alheia", location="X")
        db.add_all([school, clinic, foreign]); db.commit()
        ids = {"school": school.id, "clinic": clinic.id, "foreign": foreign.id, "org": org.id}

    def get_test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    who = {"sub": "campo"}
    app.dependency_overrides[require_identity] = lambda: who["sub"]
    try:
        yield TestClient(app), ids, who, engine, monkeypatch
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def send(client, data: bytes, **form):
    return client.post("/api/v1/documents", files={"file": ("nota.jpg", data, "image/jpeg")}, data={k: str(v) for k, v in form.items()})


def fake_claude(monkeypatch, *answers):
    """Replace the network call; returns the list of models asked, in order."""
    calls, queue = [], list(answers)
    monkeypatch.setenv("DOC_AI_PROVIDER", "anthropic")
    monkeypatch.setattr(ocr, "_client", lambda: (object(), ""))
    monkeypatch.setattr(ocr, "_ask", lambda client, model, image: (calls.append(model), queue.pop(0))[1])
    return calls


def test_access_key_check_digit():
    parsed = ocr.parse_access_key(" ".join(VALID_KEY[i:i + 4] for i in range(0, 44, 4)))  # printed in groups of 4
    assert parsed == {"access_key": VALID_KEY, "uf": "MA", "year_month": "2026-10", "cnpj": "12.345.678/0001-95",
                      "model": "NF-e", "series": "1", "number": "4321"}
    wrong = VALID_KEY[:43] + str((int(VALID_KEY[43]) + 1) % 10)
    assert ocr.parse_access_key(wrong) is None and ocr.parse_access_key("123") is None


def test_gps_suggests_the_work_without_ocr(env):
    client, ids, _, _, _ = env
    body = send(client, img(1), latitude=-5.2585, longitude=-44.6492, accuracy=15).json()
    assert body["status"] == "PENDING" and body["suggested_project_id"] == ids["school"] and body["project_id"] is None
    assert body["suggestion_reason"].startswith("Fotografado na obra") and body["engine"] is None
    far = send(client, img(2), latitude=-5.40, longitude=-44.90).json()
    assert far["suggested_project_id"] is None and "fora das obras" in far["suggestion_reason"]
    camera = send(client, img(3, gps=CLINIC), latitude=SCHOOL[0], longitude=SCHOOL[1]).json()
    assert camera["location_source"] == "EXIF" and camera["suggested_project_id"] == ids["clinic"]  # camera GPS wins
    assert send(client, img(4)).json()["suggestion_reason"] == "Sem localização: escolha a obra"


def test_ocr_prefills_and_escalates_only_when_needed(env):
    client, ids, _, _, monkeypatch = env
    calls = fake_claude(monkeypatch, reading())
    body = send(client, img(5), latitude=SCHOOL[0], longitude=SCHOOL[1]).json()
    assert calls == ["claude-haiku-5-5"] and body["kind"] == "NOTA_FISCAL" and body["problems"] == []
    assert body["draft"]["amount"] == "350.00" and body["draft"]["supplier"] == "Casa do Construtor Ltda"
    assert body["draft"]["category"] == "MATERIAL" and body["nfe"]["number"] == "4321" and body["access_key"] == VALID_KEY

    calls = fake_claude(monkeypatch, reading(total_amount=999.0, access_key=None), reading(access_key=None, confidence="medium"))
    body = send(client, img(6)).json()
    assert calls == ["claude-haiku-5-5", "claude-sonnet-5-5"] and body["engine"] == "claude-sonnet-5-5" and body["problems"] == []

    calls = fake_claude(monkeypatch, reading(access_key=VALID_KEY[:43] + "0" if VALID_KEY[43] != "0" else VALID_KEY[:43] + "1"),
                        reading(access_key="1" * 44))
    body = send(client, img(7)).json()
    assert len(calls) == 2 and body["access_key"] is None and "chave de acesso não confere" in body["problems"]


def test_failed_reading_keeps_document(env):
    client, _, _, _, monkeypatch = env
    monkeypatch.setenv("DOC_AI_PROVIDER", "anthropic")
    monkeypatch.setattr(ocr, "_client", lambda: (object(), ""))

    def down(*_):
        raise ocr.ExtractionFailed("Serviço de leitura indisponível")
    monkeypatch.setattr(ocr, "_ask", down)
    body = send(client, img(8)).json()
    assert body["status"] == "PENDING" and body["read_error"] == "Serviço de leitura indisponível" and body["draft"]["amount"] is None


def test_confirm_creates_expense_once(env):
    client, ids, _, engine, monkeypatch = env
    fake_claude(monkeypatch, reading())
    doc = send(client, img(9), latitude=SCHOOL[0], longitude=SCHOOL[1]).json()
    form = {"project_id": ids["school"], "kind": "NOTA_FISCAL", "supplier": "Casa do Construtor Ltda", "description": "Cimento CP II 50kg",
            "amount": "350.00", "expense_date": "2026-10-14", "category": "MATERIAL"}
    done = client.post(f"/api/v1/documents/{doc['id']}/confirm", json=form)
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "CONFIRMED" and done.json()["project"] == "Escola"
    assert client.post(f"/api/v1/documents/{doc['id']}/confirm", json=form).status_code == 409
    with Session(engine) as db:
        expense = db.scalar(select(Expense))
        assert expense.amount == Decimal("350.00") and expense.source_ref == "nfe:" + VALID_KEY and expense.evidence_key == "documento:" + doc["id"]

    fake_claude(monkeypatch, reading())  # same invoice photographed again
    again = send(client, img(10)).json()
    assert "esta nota fiscal já foi enviada em outro documento" in again["problems"]
    assert client.post(f"/api/v1/documents/{again['id']}/confirm", json=form).status_code == 409
    listed = client.get(f"/api/v1/projects/{ids['school']}/documents").json()
    assert [d["id"] for d in listed] == [doc["id"]]


def test_same_supplier_value_and_date_needs_explicit_ok(env):
    client, ids, _, engine, _ = env
    form = {"project_id": ids["school"], "kind": "RECIBO", "supplier": "João Pedreiro", "description": "Diária",
            "amount": "150.00", "expense_date": "2026-10-14", "category": "LABOR"}
    first, second = send(client, img(11)).json(), send(client, img(12)).json()
    assert client.post(f"/api/v1/documents/{first['id']}/confirm", json=form).status_code == 200
    assert client.post(f"/api/v1/documents/{second['id']}/confirm", json=form).status_code == 409
    assert client.post(f"/api/v1/documents/{second['id']}/confirm", json={**form, "allow_duplicate": True}).status_code == 200
    with Session(engine) as db:
        assert len(db.scalars(select(Expense)).all()) == 2


def test_quote_is_filed_without_expense_and_proof_is_paid(env):
    client, ids, _, engine, _ = env
    base = {"project_id": ids["clinic"], "supplier": "Madeireira", "description": "Madeira para telhado", "amount": "4800.00",
            "expense_date": "2026-10-10", "category": "MATERIAL"}
    quote, proof = send(client, img(13)).json(), send(client, img(14)).json()
    assert client.post(f"/api/v1/documents/{quote['id']}/confirm", json={**base, "kind": "ORCAMENTO"}).json()["expense_id"] is None
    paid = client.post(f"/api/v1/documents/{proof['id']}/confirm", json={**base, "kind": "COMPROVANTE", "allow_duplicate": True}).json()
    with Session(engine) as db:
        assert db.scalar(select(Payment)).expense_id == paid["expense_id"] and db.scalar(select(Payment)).status == "PAID"


def test_access_control_and_discard(env):
    client, ids, who, engine, _ = env
    doc = send(client, img(15)).json()
    form = {"project_id": ids["foreign"], "kind": "RECIBO", "supplier": "X", "description": "Y", "amount": "10.00", "category": "OTHER"}
    assert client.post(f"/api/v1/documents/{doc['id']}/confirm", json=form).status_code == 404   # work of another company
    who["sub"] = "viewer"
    assert client.get(f"/api/v1/documents/{doc['id']}/file").status_code == 200
    assert client.post(f"/api/v1/documents/{doc['id']}/discard").status_code == 404               # viewers only look
    who["sub"] = "outsider"
    assert client.get(f"/api/v1/documents/{doc['id']}").status_code == 404
    assert client.get("/api/v1/documents").json() == []
    who["sub"] = "campo"
    assert client.post(f"/api/v1/documents/{doc['id']}/discard").json()["status"] == "DISCARDED"
    assert client.get("/api/v1/documents").json() == []
    assert send(client, img(15)).status_code == 409                                          # same file again
    with Session(engine) as db:
        assert db.get(FieldDocument, doc["id"]).storage_key.startswith("documents/")
