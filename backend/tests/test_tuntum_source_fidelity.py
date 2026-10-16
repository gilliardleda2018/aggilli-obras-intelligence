"""Fidelity contract for the engineers' FOPAG, entirely in an isolated in-memory DB.

Never uses production data connections or commits operational data.
"""
import json
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Expense, FieldReport, LaborContract, Membership, Payment, Project
from scripts.import_tuntum import DATA, POOL, dec, run


def test_original_source_shape_and_financial_totals_are_not_rewritten():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    assert data["source"]["reference_date"] == "2026-08-28"
    assert (len(data["locations"]), len(data["payroll"]), len(data["contracts"]),
            len(data["suppliers"]), len(data["activities"])) == (14, 16, 12, 3, 7)
    assert sum((dec(c["total"]) for c in data["contracts"] if c["total"] is not None), Decimal("0")) == Decimal("736169.72")
    assert sum((dec(c["advance"]) for c in data["contracts"]), Decimal("0")) == Decimal("214383.00")


def test_import_dry_run_preserves_exact_rows_and_idempotence():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    before = json.dumps(data, sort_keys=True, ensure_ascii=False)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            first = run(db, "Grupo MG", "owner-test", "audit-test", data)
            assert db.scalar(select(func.count(Project.id))) == 15
            assert db.scalar(select(func.count(LaborContract.id))) == 12
            assert db.scalar(select(func.count(FieldReport.id))) == 7
            assert db.scalar(select(func.count(Payment.id))) == 16
            assert db.scalar(select(func.count(Payment.id)).where(Payment.status == "PAID")) == 0
            assert db.scalar(select(func.count(Payment.id)).where(Payment.status == "SCHEDULED")) == 16
            assert db.scalar(select(func.count(Project.id)).where(Project.name == POOL, Project.status == "COST_POOL")) == 1
            assert db.scalar(select(func.count(Membership.id)).where(Membership.subject_id == "owner-test")) == 1
            assert any("contracts_total" in issue for issue in first.divergences)
            assert any("contracts_advance" in issue for issue in first.divergences)
            for source_contract in data["contracts"]:
                contract = db.scalar(select(LaborContract).where(
                    LaborContract.contractor == source_contract["name"],
                    LaborContract.source_ref.like("contratos-2026-08-28:%")))
                assert contract is not None
                assert contract.total == (dec(source_contract["total"]) if source_contract["total"] is not None else None)
                assert contract.reported_advance == dec(source_contract["advance"])
                assert contract.reported_balance == dec(source_contract["balance"])
            snapshot = {
                cls.__tablename__: db.scalar(select(func.count(cls.id)))
                for cls in (Project, LaborContract, FieldReport, Expense, Payment)
            }
            again = run(db, "Grupo MG", "owner-test", "audit-test", data)
            assert not any(again.created.get(key, 0) for key in
                           ("project", "labor_contract", "field_report", "expense", "supplier_debt", "payment"))
            assert snapshot == {
                cls.__tablename__: db.scalar(select(func.count(cls.id)))
                for cls in (Project, LaborContract, FieldReport, Expense, Payment)
            }
            assert json.dumps(data, sort_keys=True, ensure_ascii=False) == before
            db.rollback()
    finally:
        engine.dispose()
