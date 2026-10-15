"""SYNTHETIC demonstration data — never mixed with real works.

Creates the organization "Demonstração (dados sintéticos)" with one clearly labelled work and ~18 weeks of
measurements, expenses and scheduled payments, so forecasting can be seen working before real history exists.

    python -m scripts.seed_demo --owner-subject dev-owner
"""
import argparse
import math
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Expense, Measurement, Membership, Organization, Payment, Project, ServiceItem

ORG = "Demonstração (dados sintéticos)"
NAME = "Galpão modelo — DADOS SINTÉTICOS"
SERVICES = [("Fundações", "m³", 120, 15), ("Estrutura metálica", "t", 40, 30), ("Cobertura", "m²", 1800, 20),
            ("Alvenaria", "m²", 900, 15), ("Instalações", "vb", 1, 10), ("Acabamentos", "m²", 1800, 10)]
# Planned window (week index) for each service; productivity drops after week 10 to make the forecast interesting.
WINDOWS = {"Fundações": (0, 5), "Estrutura metálica": (3, 13), "Cobertura": (9, 18), "Alvenaria": (10, 20),
           "Instalações": (12, 24), "Acabamentos": (18, 27)}


def run(owner: str, today: date | None = None) -> str:
    today = today or date.today()
    rng = random.Random(42)
    with SessionLocal() as db:
        org = db.scalar(select(Organization).where(Organization.name == ORG))
        if org is None:
            org = Organization(name=ORG)
            db.add(org)
            db.flush()
        if not db.scalar(select(Membership).where(Membership.organization_id == org.id, Membership.subject_id == owner)):
            db.add(Membership(organization_id=org.id, subject_id=owner, role="OWNER"))
        if db.scalar(select(Project).where(Project.organization_id == org.id, Project.name == NAME)):
            db.commit()
            return "já existe"
        start = today - timedelta(weeks=18)
        project = Project(organization_id=org.id, name=NAME, location="Tuntum/MA", municipality="Tuntum", status="IN_PROGRESS",
                          budget=Decimal("480000.00"), start_date=start, end_date=start + timedelta(weeks=26),
                          responsible="Engenheiro (demonstração)", source="SINTÉTICO — demonstração")
        db.add(project)
        db.flush()
        services = {}
        for name, unit, planned, weight in SERVICES:
            item = ServiceItem(project_id=project.id, name=name, unit=unit, planned_quantity=Decimal(planned), weight=Decimal(weight))
            db.add(item)
            services[name] = item
        db.flush()
        done = {name: 0.0 for name in services}
        for week in range(18):
            day = start + timedelta(weeks=week, days=4)
            slowdown = 1.0 if week < 10 else 0.72
            for name, (first, last) in WINDOWS.items():
                if not first <= week <= last:
                    continue
                planned = float(services[name].planned_quantity)
                pace = planned / (last - first + 1) * slowdown * rng.uniform(0.75, 1.15)
                quantity = min(planned - done[name], pace)
                if quantity <= planned * 0.001:
                    continue
                done[name] += quantity
                db.add(Measurement(service_item_id=services[name].id, quantity=Decimal(str(round(quantity, 3))), status="APPROVED",
                                   recorded_by="demo:campo", measured_on=day, decided_by="demo:engenheiro", notes="SINTÉTICO"))
            weekly_cost = 480000 / 26 * (1.12 if week >= 6 else 1.0) * rng.uniform(0.8, 1.2) * (0.9 + 0.1 * math.sin(week))
            for share, (category, supplier) in zip((0.55, 0.35, 0.10), (("MATERIAL", "Fornecedor A (sintético)"),
                                                                     ("LABOR", "Empreiteiro B (sintético)"), ("EQUIPMENT", "Locadora C (sintético)"))):
                amount = Decimal(str(round(weekly_cost * share, 2)))
                expense = Expense(project_id=project.id, description=f"Semana {week + 1} — {category.lower()} (SINTÉTICO)", supplier=supplier,
                                  amount=amount, category=category, status="OPEN", created_by="demo:financeiro", expense_date=day,
                                  source_ref=f"demo:{week}:{category}")
                db.add(expense)
                db.flush()
                paid = week < 16
                db.add(Payment(expense_id=expense.id, amount=amount, scheduled_date=day + timedelta(days=3 if paid else 10),
                               status="PAID" if paid else "SCHEDULED", reference="SINTETICO" if paid else None, created_by="demo:financeiro",
                               confirmed_by="demo:financeiro" if paid else None))
        db.commit()
        return project.id


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--owner-subject", required=True)
    args = parser.parse_args(argv)
    print("Obra sintética:", run(args.owner_subject))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
