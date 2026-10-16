"""Spreadsheet import: messy real-world sheets understood, previewed, confirmed once, forecasts fed."""
import io
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import spreadsheet
from app.classifier import Classifier, by_rules
from app.db import Base, get_db
from app.main import app
from app.models import Expense, Measurement, Membership, Organization, Payment, Project, ServiceItem
from app.security import require_identity

CSV = """FOPAG SEMANAL 28/AGOSTO/2026;;;;
;;;;
Data;Obra;Fornecedor;Descrição;Valor;Situação
28/08/2026;CASA BARRA;Darlan;Cimento, rejunte e conexões;R$ 935,00;pago
28/08/2026;Tabocal;Laércio;Pintura e acabamento;2.000,00;
29/08/2026;diversas obras;Posto Ana Luiza;Abastecimento diesel;985,87;
;;;;
;;Total;;3.920,87;
30/08/2026;Obra que não existe;Fulano;Serviço qualquer;100,00;
"""


def test_parsers_understand_brazilian_formats():
    assert spreadsheet.parse_money("R$ 1.234,56") == Decimal("1234.56")
    assert spreadsheet.parse_money("2.000,00") == Decimal("2000.00")
    assert spreadsheet.parse_money("985.87") == Decimal("985.87")
    assert spreadsheet.parse_money(1500) == Decimal("1500.00")
    assert spreadsheet.parse_date("28/08/2026") == date(2026, 8, 28)
    assert spreadsheet.parse_date(46262) == date(2026, 8, 28)  # Excel serial
    names = {"a": "Casa BDC / Casa Barra", "b": "MG Tabocal", "c": "MG Coco — Garagem"}
    assert spreadsheet.match_project("CASA BARRA", names)[0] == "a"
    assert spreadsheet.match_project("tabocal", names)[0] == "b"
    assert spreadsheet.match_project("Galpão MG Coco garagem", names)[0] == "c"
    assert spreadsheet.match_project("Prefeitura", names)[0] is None


def test_classifier_rules_and_learning():
    assert by_rules("Posto Ana Luiza abastecimento")[0] == "FUEL"
    assert by_rules("6 horas de munck")[0] == "EQUIPMENT"
    assert by_rules("Cimento e areia")[0] == "MATERIAL"
    samples = [(f"Loja Alfa item {i}", "MATERIAL") for i in range(12)] + [(f"Equipe Beta diária {i}", "LABOR") for i in range(12)]
    model = Classifier(samples)
    assert model.model is not None and model.suggest("Loja Alfa item novo")["category"] == "MATERIAL"
    assert Classifier(samples[:5]).model is None  # too few examples → rules only


@pytest.fixture()
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org, other = Organization(name="Grupo MG"), Organization(name="Outra")
        db.add_all([org, other]); db.flush()
        db.add_all([Membership(organization_id=org.id, subject_id="darlan", role="FIELD_OPERATOR"),
                    Membership(organization_id=org.id, subject_id="viewer", role="VIEWER"),
                    Membership(organization_id=other.id, subject_id="outsider", role="OWNER")])
        projects = [Project(organization_id=org.id, name=n, location="Tuntum/MA", status=s) for n, s in
                    (("Casa BDC / Casa Barra", "IN_PROGRESS"), ("MG Tabocal", "IN_PROGRESS"), ("Despesas comuns — a ratear", "COST_POOL"))]
        db.add_all(projects); db.flush()
        db.add(ServiceItem(project_id=projects[1].id, name="Estrutura do galpão", unit="t", planned_quantity=Decimal(20), weight=Decimal(100)))
        db.commit()
        ids = {p.name: p.id for p in projects}

    def get_test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    who = {"sub": "darlan"}
    app.dependency_overrides[require_identity] = lambda: who["sub"]
    try:
        yield TestClient(app), engine, ids, who
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def upload(client, content: bytes, name: str, **form):
    return client.post("/api/v1/imports/preview", files={"file": (name, content)}, data=form)


def test_csv_preview_commit_and_no_duplicates(env):
    client, engine, ids, _ = env
    response = upload(client, CSV.encode("utf-8"), "fopag.csv")
    assert response.status_code == 201, response.text
    body = response.json()
    rows = {r["line"]: r for r in body["rows"]}
    assert body["summary"]["kind"] == "expenses" and body["summary"]["valid"] == 3 and body["summary"]["with_issues"] == 1
    assert rows[4]["project"] == "Casa BDC / Casa Barra" and rows[4]["paid"] is True and rows[4]["category"] == "MATERIAL"
    assert rows[6]["project"] == "Despesas comuns — a ratear" and rows[6]["category"] == "FUEL"
    assert rows[9]["ok"] is False and "obra não identificada" in rows[9]["issues"][0]
    assert body["summary"]["total"] == "3920.87"  # the "Total" line of the sheet is not imported as an expense
    with Session(engine) as db:
        assert db.scalar(select(func.count(Expense.id))) == 0  # preview writes nothing operational
    result = client.post(f"/api/v1/imports/{body['id']}/commit", json={"overrides": {"5": {"category": "LABOR"}}}).json()
    assert (result["created"], result["skipped"]) == (3, 1)
    with Session(engine) as db:
        assert db.scalar(select(Expense.category).where(Expense.supplier == "Laércio")) == "LABOR"
        assert db.scalar(select(func.count(Payment.id)).where(Payment.status == "PAID")) == 0  # spreadsheet claims are not verified payments
        declared = db.scalar(select(Payment).join(Expense).where(Expense.supplier == "Darlan"))
        assert declared is not None and declared.status == "SCHEDULED"
        assert declared.confirmed_by is None
        assert "não comprovado" in declared.reference
    assert client.post(f"/api/v1/imports/{body['id']}/commit", json={}).status_code == 409
    again = upload(client, CSV.encode("utf-8"), "fopag.csv").json()
    assert all(r.get("duplicate") for r in again["rows"] if r["project"])  # same file → flagged, never duplicated


def test_xlsx_measurements_import_as_pending(env):
    client, engine, ids, who = env
    book = Workbook()
    sheet = book.active
    sheet.append(["Medição semanal — Tabocal"])
    sheet.append(["Data", "Obra", "Serviço", "Quantidade", "Unidade"])
    sheet.append([date(2026, 10, 1), "MG Tabocal", "estrutura do galpao", 4, "t"])
    sheet.append([date(2026, 10, 8), "MG Tabocal", "Cobertura", 2, "m²"])
    buffer = io.BytesIO()
    book.save(buffer)
    body = upload(client, buffer.getvalue(), "medicao.xlsx").json()
    assert body["summary"]["kind"] == "measurements" and body["summary"]["valid"] == 1
    assert "serviço não encontrado" in body["rows"][1]["issues"][0]
    assert client.post(f"/api/v1/imports/{body['id']}/commit", json={}).json()["created"] == 1
    with Session(engine) as db:
        assert db.scalar(select(Measurement.status)) == "PENDING"  # still needs the engineer's approval


def test_permissions_and_limits(env):
    client, _, ids, who = env
    assert upload(client, b"abc", "notas.pdf").status_code == 422
    assert upload(client, b"x;y\n1;2\n", "vazia.csv").status_code == 422
    who["sub"] = "viewer"
    assert upload(client, CSV.encode(), "fopag.csv").status_code == 404
    who["sub"] = "outsider"
    batch = None
    who["sub"] = "darlan"
    batch = upload(client, CSV.encode(), "fopag.csv").json()["id"]
    who["sub"] = "outsider"
    assert client.get(f"/api/v1/imports/{batch}").status_code == 404
    assert client.post(f"/api/v1/imports/{batch}/commit", json={}).status_code == 404


def test_manual_project_override_recovers_missing_project_only(env):
    client, engine, ids, _ = env
    response = upload(client, CSV.encode("utf-8"), "override.csv")
    assert response.status_code == 201
    batch = response.json()
    missing = next(row for row in batch["rows"] if row["line"] == 9)
    assert not missing["ok"] and missing["project_id"] is None
    result = client.post(f"/api/v1/imports/{batch['id']}/commit", json={
        "overrides": {"9": {"project_id": ids["MG Tabocal"]}}
    })
    assert result.status_code == 200, result.text
    assert result.json()["created"] == 4
    with Session(engine) as db:
        expense = db.scalar(select(Expense).where(Expense.supplier == "Fulano"))
        assert expense is not None and expense.project_id == ids["MG Tabocal"]


def test_manual_project_override_does_not_bypass_invalid_amount(env):
    client, engine, ids, _ = env
    csv_data = "Data;Obra;Fornecedor;Descrição;Valor\n28/08/2026;Obra inexistente;Teste;Serviço;inválido\n"
    response = upload(client, csv_data.encode(), "invalid.csv")
    assert response.status_code == 201, response.text
    batch = response.json()
    result = client.post(f"/api/v1/imports/{batch['id']}/commit", json={
        "overrides": {"2": {"project_id": ids["MG Tabocal"]}}
    })
    assert result.status_code == 200
    assert result.json()["created"] == 0
    with Session(engine) as db:
        assert db.scalar(select(func.count(Expense.id))) == 0


def test_multi_organization_requires_explicit_context(env):
    client, engine, ids, who = env
    with Session(engine) as db:
        other = db.scalar(select(Organization).where(Organization.name == "Outra"))
        db.add(Membership(organization_id=other.id, subject_id="darlan", role="ADMIN"))
        db.commit()
        other_id = other.id
    ambiguous = upload(client, CSV.encode("utf-8"), "ambiguous.csv")
    assert ambiguous.status_code == 422
    assert "organização" in ambiguous.json()["detail"]
    resolved = upload(client, CSV.encode("utf-8"), "explicit.csv", organization_id=other_id)
    assert resolved.status_code == 201, resolved.text
    assert resolved.json()["summary"]["valid"] == 0


def test_override_cannot_move_expense_to_other_organization(env):
    client, engine, ids, _ = env
    with Session(engine) as db:
        other = db.scalar(select(Organization).where(Organization.name == "Outra"))
        foreign = Project(organization_id=other.id, name="Foreign Work", location="Other")
        db.add(foreign)
        db.commit()
        foreign_id = foreign.id
    batch = upload(client, CSV.encode("utf-8"), "foreign-override.csv").json()
    result = client.post(f"/api/v1/imports/{batch['id']}/commit", json={
        "overrides": {"9": {"project_id": foreign_id}}
    })
    assert result.status_code == 200, result.text
    assert result.json()["created"] == 3
    with Session(engine) as db:
        assert db.scalar(select(Expense.id).where(Expense.project_id == foreign_id)) is None


def test_explicit_foreign_organization_is_not_accessible(env):
    client, engine, _, _ = env
    with Session(engine) as db:
        other = db.scalar(select(Organization).where(Organization.name == "Outra"))
        other_id = other.id
    response = upload(client, CSV.encode("utf-8"), "foreign-org.csv", organization_id=other_id)
    assert response.status_code == 404


def test_fopag_contract_reconciliation_reports_without_changing_source():
    from scripts.import_tuntum import DATA, run
    import json
    from app.models import Organization
    from sqlalchemy.orm import Session
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    source = json.loads(DATA.read_text(encoding="utf-8"))
    original = json.dumps(source, sort_keys=True)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            report = run(db, "Grupo MG", "owner-test", "audit-test", source)
            assert any("Raimundo BR" in issue for issue in report.divergences)
            assert any("Cabiludo" in issue for issue in report.divergences)
            assert any("contracts_total" in issue for issue in report.divergences)
            assert json.dumps(source, sort_keys=True) == original
            db.rollback()
    finally:
        engine.dispose()


def test_financial_closing_preview_reads_persisted_payments_without_writing(env):
    client, engine, ids, who = env
    who["sub"] = "darlan"
    with Session(engine) as db:
        db.add(Membership(organization_id=db.scalar(select(Project.organization_id).where(
            Project.id == ids["MG Tabocal"])), subject_id="finance-owner", role="OWNER"))
        db.commit()
    who["sub"] = "finance-owner"
    expense = client.post(f'/api/v1/projects/{ids["MG Tabocal"]}/expenses', json={
        "description": "Serviço de teste", "supplier": "Fornecedor teste",
        "amount": "100.00", "category": "SERVICE"}).json()
    assert expense["id"]
    payment = client.post(f'/api/v1/expenses/{expense["id"]}/payments', json={
        "amount": "40.00", "scheduled_date": "2026-10-16"}).json()
    assert payment["status"] == "SCHEDULED"
    before = client.get(f'/api/v1/projects/{ids["MG Tabocal"]}/finance/closing-preview')
    assert before.status_code == 200
    assert before.json()["rows"][0]["remaining"] == "100.00"
    assert before.json()["rows"][0]["scheduled"] == "40.00"
    confirmed = client.post(f'/api/v1/payments/{payment["id"]}/confirm', json={
        "reference": "SIMULATED-REFERENCE-001"})
    assert confirmed.status_code == 200
    after = client.get(f'/api/v1/projects/{ids["MG Tabocal"]}/finance/closing-preview')
    assert after.status_code == 200
    assert after.json()["rows"][0]["paid"] == "40.00"
    assert after.json()["rows"][0]["remaining"] == "60.00"
    assert after.json()["closed"] is False and after.json()["money_moved"] is False
