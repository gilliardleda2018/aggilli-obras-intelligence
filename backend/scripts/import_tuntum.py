"""Import the Tuntum reference records (FOPAG 28/08/2026) into the database — dry run unless --apply.

Usage (from backend/):
    python -m scripts.import_tuntum --organization "Grupo MG" --owner-subject <sub>          # dry run
    python -m scripts.import_tuntum --organization "Grupo MG" --owner-subject <sub> --apply  # write

Rules:
- Idempotent: every record carries a source reference; running again skips what already exists.
- Weekly FOPAG lines become an expense plus a SCHEDULED payment (never PAID: there is no bank evidence).
- Supplier lines that pay down a reported debt are NOT imported as separate expenses: the debt becomes
  one open expense and the FOPAG line becomes a scheduled payment against it (no double counting).
- "Diversas obras" goes to a COST_POOL work, flagged for apportionment; nothing is split automatically.
- Budgets, dates and coordinates are left empty: they are not in the source and are never invented.
"""
import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import AuditEvent, Expense, FieldReport, LaborContract, Membership, Organization, Payment, Project, User

DATA = Path(__file__).resolve().parents[1] / "data" / "tuntum_2026-08-28.json"
POOL = "Despesas comuns — a ratear"
SHARED = "Diversas obras"
CATEGORIES = {"Mão de obra": "LABOR", "Material": "MATERIAL", "Serviço": "SERVICE", "Combustível": "FUEL",
              "Equipamento": "EQUIPMENT", "Outros": "OTHER"}
# Totals stated in the source document (docs/IMPORTACAO-TUNTUM-2026.md), used only to report divergences.
DOCUMENTED = {"labor": Decimal("11950.00"), "other": Decimal("19620.87"), "weekly": Decimal("31570.87"),
              "contracts_total": Decimal("730169.72"), "contracts_advance": Decimal("195790.00")}


@dataclass
class Report:
    created: dict = field(default_factory=dict)
    skipped: dict = field(default_factory=dict)
    divergences: list = field(default_factory=list)

    def add(self, kind: str, created: bool):
        target = self.created if created else self.skipped
        target[kind] = target.get(kind, 0) + 1


def dec(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def run(db: Session, organization: str, owner: str, actor: str, data: dict) -> Report:
    report = Report()
    reference = date.fromisoformat(data["source"]["reference_date"])
    source = "FOPAG " + reference.strftime("%d/%m/%Y")
    municipality = data["source"]["municipality"]
    location = f"{municipality}/{data['source']['state']}"

    org = db.scalar(select(Organization).where(Organization.name == organization))
    report.add("organization", org is None)
    if org is None:
        org = Organization(name=organization)
        db.add(org)
        db.flush()
    if not db.scalar(select(Membership).where(Membership.organization_id == org.id, Membership.subject_id == owner)):
        db.add(Membership(organization_id=org.id, subject_id=owner, role="OWNER"))
        report.add("owner_membership", True)

    def audit(action: str, resource: str):
        db.add(AuditEvent(organization_id=org.id, subject_id=actor, action=action, resource_id=resource))

    projects: dict[str, Project] = {}
    for name, status in [(name, "IN_PROGRESS") for name in data["locations"]] + [(POOL, "COST_POOL")]:
        project = db.scalar(select(Project).where(Project.organization_id == org.id, Project.name == name))
        report.add("project", project is None)
        if project is None:
            project = Project(organization_id=org.id, name=name, location=location, municipality=municipality,
                              status=status, source=source)
            db.add(project)
            db.flush()
            audit("project.import", project.id)
        projects[name] = project

    def project_of(name: str) -> Project:
        return projects[POOL if name == SHARED else name]

    def expense(project: Project, ref: str, **values) -> tuple[Expense, bool]:
        existing = db.scalar(select(Expense).where(Expense.project_id == project.id, Expense.source_ref == ref))
        if existing:
            return existing, False
        item = Expense(project_id=project.id, source_ref=ref, created_by=actor, expense_date=reference, **values)
        db.add(item)
        db.flush()
        audit("expense.import", item.id)
        return item, True

    def scheduled(item: Expense, amount: Decimal):
        if db.scalar(select(Payment).where(Payment.expense_id == item.id, Payment.scheduled_date == reference)):
            report.add("payment", False)
            return
        payment = Payment(expense_id=item.id, amount=amount, scheduled_date=reference, created_by=actor)
        db.add(payment)
        db.flush()
        audit("payment.import_scheduled", payment.id)
        report.add("payment", True)

    debts = {supplier["name"]: supplier for supplier in data["suppliers"]}
    for index, line in enumerate(data["payroll"], start=1):
        amount = dec(line["amount"])
        project = project_of(line["project"])
        if line["name"] in debts:
            debt = debts[line["name"]]
            item, created = expense(project, "fornecedor:" + line["name"], supplier=line["name"],
                                    description="Saldo devedor relatado ao fornecedor", amount=dec(debt["debt"]),
                                    category=CATEGORIES[line["category"]], status="OPEN",
                                    notes=(line.get("notes") or "Dívida relatada; conciliar com o fornecedor")[:500])
            report.add("supplier_debt", created)
        else:
            item, created = expense(project, f"fopag-{reference.isoformat()}:{index}", supplier=line["name"],
                                    description=line["work"], amount=amount, category=CATEGORIES[line["category"]],
                                    status="OPEN", notes=(line.get("notes") or None))
            report.add("expense", created)
        scheduled(item, amount)

    for index, contract in enumerate(data["contracts"], start=1):
        project = project_of(contract["project"])
        ref = f"contratos-{reference.isoformat()}:{index}"
        exists = db.scalar(select(LaborContract).where(LaborContract.project_id == project.id, LaborContract.source_ref == ref))
        report.add("labor_contract", exists is None)
        if exists is None:
            item = LaborContract(project_id=project.id, contractor=contract["name"],
                                 total=None if contract["total"] is None else dec(contract["total"]),
                                 reported_advance=dec(contract["advance"]), reported_balance=dec(contract["balance"]),
                                 source_ref=ref, created_by=actor)
            db.add(item)
            db.flush()
            audit("labor_contract.import", item.id)

    for activity in data["activities"]:
        project = project_of(activity["project"])
        summary = "Relato do contratante: " + activity["description"]
        exists = db.scalar(select(FieldReport).where(FieldReport.project_id == project.id, FieldReport.summary == summary))
        report.add("field_report", exists is None)
        if exists is None:
            item = FieldReport(project_id=project.id, report_date=reference, weather="Não informado", summary=summary,
                               recorded_by=actor)
            db.add(item)
            db.flush()
            audit("field_report.import", item.id)

    labor = sum(dec(line["amount"]) for line in data["payroll"] if line["category"] == "Mão de obra")
    weekly = sum(dec(line["amount"]) for line in data["payroll"])
    found = {"labor": labor, "other": weekly - labor, "weekly": weekly,
             "contracts_total": sum(dec(c["total"]) for c in data["contracts"] if c["total"] is not None),
             "contracts_advance": sum(dec(c["advance"]) for c in data["contracts"])}
    report.divergences = [f"{key}: linha TOTAL do documento {DOCUMENTED[key]} x soma das linhas {found[key]}" for key in DOCUMENTED
                          if DOCUMENTED[key] != found[key]]
    # Preserve source values; flag contract-level inconsistencies for manual reconciliation.
    for contract in data["contracts"]:
        if contract.get("total") is None:
            continue
        expected = dec(contract["total"]) - dec(contract["advance"])
        stated = dec(contract["balance"])
        if expected != stated:
            report.divergences.append(
                f"contrato {contract['name']} ({contract['project']}): saldo informado {stated} x total menos adiantamento {expected}"
            )
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--organization", required=True)
    parser.add_argument("--owner-subject", required=True, help="identity subject (sub) that receives OWNER")
    parser.add_argument("--actor", default="import:tuntum-2026-08-28")
    parser.add_argument("--apply", action="store_true", help="write to the database (default: dry run)")
    parser.add_argument("--preserve-declared-divergences", action="store_true")
    args = parser.parse_args(argv)
    data = json.loads(DATA.read_text(encoding="utf-8"))
    with SessionLocal() as db:
        if args.apply:
            owner = db.scalar(select(User).where(User.id == args.owner_subject))
            org = db.scalar(select(Organization).where(Organization.name == args.organization))
            authorized = db.scalar(select(Membership.id).where(
                Membership.organization_id == org.id,
                Membership.subject_id == args.owner_subject,
                Membership.role == "OWNER")) if org else None
            if not owner or not owner.active or not authorized:
                print("BLOQUEADO: proprietário ativo existente obrigatório")
                return 2
        report = run(db, args.organization, args.owner_subject, args.actor, data)
        if args.apply and report.divergences and not args.preserve_declared_divergences:
            db.rollback()
            print("BLOQUEADO: divergências documentais requerem confirmação explícita")
            return 2
        if args.apply:
            if report.divergences:
                for index, issue in enumerate(report.divergences, 1):
                    db.add(AuditEvent(organization_id=org.id, subject_id=args.owner_subject,
                                      action="fopag.source_divergence_unresolved",
                                      resource_id=f"tuntum-2026-08-28:{index}"))
                print("DIVERGÊNCIAS PRESERVADAS E NÃO CONCILIADAS")
            db.commit()
        else:
            db.rollback()
    print(("GRAVADO" if args.apply else "SIMULAÇÃO (nada gravado; use --apply)"))
    print("criados:", report.created)
    print("já existentes:", report.skipped)
    for line in report.divergences:
        print("DIVERGÊNCIA a conferir na fonte —", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
