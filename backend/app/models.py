import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)

class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "subject_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)

PROJECT_STATUSES = ("PLANNED", "IN_PROGRESS", "PAUSED", "DONE", "COST_POOL")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (CheckConstraint("status IN ('PLANNED','IN_PROGRESS','PAUSED','DONE','COST_POOL')",
                                      name="ck_projects_status"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(300), nullable=False)
    # Budget and dates are optional: imported works may not have them yet and they are never invented.
    budget: Mapped[Decimal | None] = mapped_column(Numeric(16,2), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # COST_POOL groups shared expenses that still need to be apportioned between works.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS", server_default="IN_PROGRESS")
    responsible: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cost_center: Mapped[str | None] = mapped_column(String(60), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9,6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9,6), nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)

class ServiceItem(Base):
    __tablename__ = "service_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(16,3), nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(7,4), nullable=False)

class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (CheckConstraint("status IN ('PENDING','APPROVED','REJECTED')", name="ck_measurements_status"),
                      CheckConstraint("quantity > 0", name="ck_measurements_quantity"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    service_item_id: Mapped[str] = mapped_column(ForeignKey("service_items.id"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(16,3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    measured_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)

class Material(Base):
    __tablename__ = "materials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)

class StockMovement(Base):
    __tablename__ = "stock_movements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    material_id: Mapped[str] = mapped_column(ForeignKey("materials.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(3), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(16,3), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)

class CostEntry(Base):
    __tablename__ = "cost_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(16,2), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)

class FieldReport(Base):
    __tablename__ = "field_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    weather: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[str] = mapped_column(String(5000), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)

class Inspection(Base):
    __tablename__ = "inspections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)

class LaborContract(Base):
    """Labor contract (empreitada). Advance/balance are kept exactly as reported by the source document."""
    __tablename__ = "labor_contracts"
    __table_args__ = (UniqueConstraint("project_id", "source_ref", name="uq_labor_contracts_source"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    contractor: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    total: Mapped[Decimal | None] = mapped_column(Numeric(16,2), nullable=True)  # not always in the source
    reported_advance: Mapped[Decimal | None] = mapped_column(Numeric(16,2), nullable=True)
    reported_balance: Mapped[Decimal | None] = mapped_column(Numeric(16,2), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)

class Expense(Base):
    __tablename__="expenses"
    __table_args__=(UniqueConstraint("project_id","source_ref",name="uq_expenses_source"),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id:Mapped[str]=mapped_column(ForeignKey("projects.id"),nullable=False,index=True)
    description:Mapped[str]=mapped_column(String(300),nullable=False)
    supplier:Mapped[str]=mapped_column(String(200),nullable=False)
    amount:Mapped[Decimal]=mapped_column(Numeric(16,2),nullable=False)
    category:Mapped[str]=mapped_column(String(20),nullable=False)
    evidence_key:Mapped[str|None]=mapped_column(String(500),nullable=True)
    status:Mapped[str]=mapped_column(String(20),nullable=False,default="OPEN")
    created_by:Mapped[str]=mapped_column(String(200),nullable=False)
    expense_date:Mapped[date|None]=mapped_column(Date,nullable=True)
    notes:Mapped[str|None]=mapped_column(String(500),nullable=True)
    contract_id:Mapped[str|None]=mapped_column(ForeignKey("labor_contracts.id",name="fk_expenses_contract"),nullable=True)
    source_ref:Mapped[str|None]=mapped_column(String(120),nullable=True)

class Payment(Base):
    __tablename__="payments"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    expense_id:Mapped[str]=mapped_column(ForeignKey("expenses.id"),nullable=False,index=True)
    amount:Mapped[Decimal]=mapped_column(Numeric(16,2),nullable=False)
    scheduled_date:Mapped[date]=mapped_column(Date,nullable=False)
    status:Mapped[str]=mapped_column(String(20),nullable=False,default="SCHEDULED")
    reference:Mapped[str|None]=mapped_column(String(200),nullable=True)
    created_by:Mapped[str]=mapped_column(String(200),nullable=False)
    confirmed_by:Mapped[str|None]=mapped_column(String(200),nullable=True)
