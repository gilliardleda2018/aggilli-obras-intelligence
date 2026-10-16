"""Production import must never create a synthetic owner or silently accept discrepancies."""
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Expense, Organization, Payment
from scripts import import_tuntum


def test_apply_rejects_unknown_owner_without_writes(monkeypatch, capsys):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(import_tuntum, "SessionLocal", lambda: Session(engine))
    try:
        result = import_tuntum.main(["--organization", "Grupo MG", "--owner-subject", "audit-only",
                                      "--apply", "--preserve-declared-divergences"])
        assert result == 2
        assert "BLOQUEADO" in capsys.readouterr().out
        with Session(engine) as db:
            assert db.scalar(select(func.count(Organization.id))) == 0
            assert db.scalar(select(func.count(Expense.id))) == 0
            assert db.scalar(select(func.count(Payment.id))) == 0
    finally:
        engine.dispose()
