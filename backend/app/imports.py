"""Spreadsheet import: upload → automatic understanding (columns, works, categories, duplicates) → preview → confirm.

Nothing is written to the operational tables until the user confirms the preview. Confirmed rows carry a
source reference (file hash + row) so importing the same file again never duplicates entries.
"""
import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import spreadsheet
from .classifier import Classifier
from .db import get_db
from .models import AuditEvent, Expense, ImportBatch, Measurement, Membership, Payment, Project, ServiceItem
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["imports"])
WRITE_ROLES = ["OWNER", "ADMIN", "ENGINEER", "FIELD_OPERATOR"]
MAX_BYTES = 5 * 1024 * 1024


def _organization(db: Session, subject: str, organization_id: str | None) -> str:
    query = select(Membership.organization_id).where(Membership.subject_id == subject, Membership.role.in_(WRITE_ROLES))
    orgs = list(db.scalars(query).all())
    if organization_id:
        if organization_id not in orgs:
            raise HTTPException(status_code=404, detail="Organization not found")
        return organization_id
    if not orgs:
        raise HTTPException(status_code=404, detail="Organization not found")
    return orgs[0]


def _projects(db: Session, organization_id: str) -> dict[str, Project]:
    return {p.id: p for p in db.scalars(select(Project).where(Project.organization_id == organization_id)).all()}


def _cell(row: list, mapping: dict, field: str):
    index = mapping.get(field)
    return row[index] if index is not None and index < len(row) else None


@router.post("/imports/preview", status_code=201)
async def preview(file: UploadFile = File(...), default_project_id: str | None = Form(None), organization_id: str | None = Form(None),
                  subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    name = (file.filename or "planilha")[:200]
    if not name.lower().endswith((".csv", ".xlsx", ".xlsm")):
        raise HTTPException(status_code=422, detail="Envie um arquivo .xlsx ou .csv")
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo acima de 5 MB")
    org_id = _organization(db, subject, organization_id)
    projects = _projects(db, org_id)
    if default_project_id and default_project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        table = spreadsheet.read_table(content, name)
    except Exception:
        raise HTTPException(status_code=422, detail="Não foi possível ler a planilha") from None
    header_index, mapping = spreadsheet.detect_header(table)
    kind = "measurements" if "quantity" in mapping and "amount" not in mapping else "expenses"
    required = {"expenses": ["amount"], "measurements": ["quantity", "description"]}[kind]
    if header_index < 0 or any(field not in mapping for field in required):
        raise HTTPException(status_code=422, detail="Não encontrei as colunas necessárias (ex.: Valor para despesas; Serviço e Quantidade para medições)")
    file_hash = hashlib.sha256(content).hexdigest()
    names = {pid: p.name for pid, p in projects.items()}
    samples = [(f"{e.supplier} {e.description}", e.category) for e in db.scalars(
        select(Expense).where(Expense.project_id.in_(list(projects)))).all()] if projects else []
    classifier = Classifier(samples)
    pool = next((pid for pid, p in projects.items() if p.status == "COST_POOL"), None)
    rows, last_project = [], None
    for offset, row in enumerate(table[header_index + 1:], start=header_index + 2):
        if not any(cell not in (None, "") for cell in row):
            continue
        issues, item = [], {"line": offset}
        project_text = str(_cell(row, mapping, "project") or "").strip()
        if project_text:
            if spreadsheet.normalize(project_text) in ("diversas obras", "diversas", "varias obras", "geral") and pool:
                pid, score = pool, 1.0
            else:
                pid, score = spreadsheet.match_project(project_text, names)
            last_project = pid or last_project
        else:
            pid, score = (default_project_id or last_project), None
        if not pid:
            pid = default_project_id
        item.update(project_text=project_text, project_id=pid, project=names.get(pid), project_score=score)
        if not pid:
            issues.append("obra não identificada — escolha uma obra padrão")
        when = spreadsheet.parse_date(_cell(row, mapping, "date"))
        item["date"] = when.isoformat() if when else None
        description = str(_cell(row, mapping, "description") or "").strip()[:300]
        item["notes"] = str(_cell(row, mapping, "notes") or "").strip()[:500] or None
        if kind == "expenses":
            amount = spreadsheet.parse_money(_cell(row, mapping, "amount"))
            supplier = str(_cell(row, mapping, "supplier") or "").strip()[:200]
            if any(spreadsheet.normalize(text).startswith(("total", "subtotal", "saldo", "soma")) for text in (supplier, description, project_text)):
                continue  # summary lines of the sheet, not expenses
            if amount is None or amount <= 0:
                if not supplier and not description:
                    continue  # totals/blank lines
                issues.append("valor ausente ou inválido")
            if not supplier and not description:
                issues.append("sem fornecedor e sem descrição")
            explicit = spreadsheet.category_from_text(_cell(row, mapping, "category"))
            suggestion = ({"category": explicit, "confidence": 1.0, "method": "planilha", "reason": "coluna de categoria"}
                          if explicit else classifier.suggest(f"{supplier} {description}"))
            if not when:
                issues.append("sem data — a despesa entra sem data e não alimenta a curva de custo")
            item.update(supplier=supplier or "Não informado", description=description or supplier, amount=str(amount) if amount else None,
                        category=suggestion["category"], classification=suggestion,
                        paid=spreadsheet.is_paid(_cell(row, mapping, "status")),
                        reference=str(_cell(row, mapping, "reference") or "").strip()[:200] or None)
            ref = f"planilha:{file_hash[:16]}:{offset}"
            if pid and db.scalar(select(Expense.id).where(Expense.project_id == pid, Expense.source_ref == ref)):
                issues.append("já importada anteriormente (mesmo arquivo e linha)")
                item["duplicate"] = True
        else:
            quantity = spreadsheet.parse_quantity(_cell(row, mapping, "quantity"))
            service_id = None
            if pid:
                services = {s.id: s.name for s in db.scalars(select(ServiceItem).where(ServiceItem.project_id == pid)).all()}
                service_id, _ = spreadsheet.match_project(description, services)
            if quantity is None or quantity <= 0:
                issues.append("quantidade ausente ou inválida")
            if not service_id:
                issues.append("serviço não encontrado na obra — cadastre-o em Medições")
            if when and when > date.today():
                issues.append("data no futuro")
            item.update(service=description, service_id=service_id, quantity=str(quantity) if quantity else None,
                        unit=str(_cell(row, mapping, "unit") or "").strip()[:30] or None)
        item["issues"] = issues
        item["ok"] = not [i for i in issues if not i.startswith("sem data")]
        rows.append(item)
        if len(rows) >= spreadsheet.MAX_ROWS:
            break
    valid = [r for r in rows if r["ok"]]
    summary = {"kind": kind, "columns": {field: str(table[header_index][index]) for field, index in mapping.items()},
               "rows": len(rows), "valid": len(valid), "with_issues": len(rows) - len(valid),
               "total": str(sum((Decimal(r["amount"]) for r in valid if r.get("amount")), Decimal(0))) if kind == "expenses" else None,
               "projects": sorted({r["project"] for r in valid if r.get("project")}),
               "classifier": {"trained_on": classifier.trained_on, "method": "modelo" if classifier.model else "regras"}}
    batch = ImportBatch(organization_id=org_id, created_by=subject, filename=name, file_hash=file_hash, kind=kind,
                        rows=json.dumps(rows, ensure_ascii=False), summary=json.dumps(summary, ensure_ascii=False))
    db.add(batch)
    db.flush()
    db.add(AuditEvent(organization_id=org_id, subject_id=subject, action="import.preview", resource_id=batch.id))
    db.commit()
    return {"id": batch.id, "filename": name, "summary": summary, "rows": rows}


@router.get("/imports/{batch_id}")
def get_batch(batch_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    batch = db.get(ImportBatch, batch_id)
    if not batch or batch.organization_id not in _member_orgs(db, subject):
        raise HTTPException(status_code=404, detail="Import not found")
    return {"id": batch.id, "filename": batch.filename, "status": batch.status, "summary": json.loads(batch.summary),
            "rows": json.loads(batch.rows), "created_at": batch.created_at.isoformat()}


def _member_orgs(db: Session, subject: str) -> list[str]:
    return list(db.scalars(select(Membership.organization_id).where(Membership.subject_id == subject,
                                                                    Membership.role.in_(WRITE_ROLES))).all())


class Commit(BaseModel):
    overrides: dict[int, dict] = Field(default_factory=dict)  # line → {"category": ..., "project_id": ...}


@router.post("/imports/{batch_id}/commit")
def commit(batch_id: str, payload: Commit, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    batch = db.scalar(select(ImportBatch).where(ImportBatch.id == batch_id).with_for_update())
    if not batch or batch.organization_id not in _member_orgs(db, subject):
        raise HTTPException(status_code=404, detail="Import not found")
    if batch.status != "PREVIEW":
        raise HTTPException(status_code=409, detail="Import already decided")
    projects = _projects(db, batch.organization_id)
    created = skipped = 0
    for row in json.loads(batch.rows):
        override = payload.overrides.get(row["line"], {})
        pid = override.get("project_id") or row.get("project_id")
        # A manual project selection resolves only the missing-project issue.
        # All other validation failures remain blocking.
        blocking = [issue for issue in row.get("issues", [])
                    if not issue.startswith("sem data") and
                    not (pid in projects and issue.startswith("obra não identificada"))]
        if blocking or row.get("duplicate") or pid not in projects:
            skipped += 1
            continue
        if batch.kind == "expenses" and (not row.get("amount") or Decimal(row["amount"]) <= 0):
            skipped += 1
            continue
        ref = f"planilha:{batch.file_hash[:16]}:{row['line']}"
        when = date.fromisoformat(row["date"]) if row.get("date") else None
        if batch.kind == "expenses":
            if db.scalar(select(Expense.id).where(Expense.project_id == pid, Expense.source_ref == ref)):
                skipped += 1
                continue
            category = override.get("category") or row["category"]
            expense = Expense(project_id=pid, supplier=row["supplier"], description=row["description"], amount=Decimal(row["amount"]),
                              category=category if category in ("MATERIAL", "LABOR", "FUEL", "EQUIPMENT", "SERVICE", "OTHER") else "OTHER",
                              status="OPEN", created_by=subject, expense_date=when, notes=row.get("notes"),
                              source_ref=ref, evidence_key=row.get("reference"))
            db.add(expense)
            db.flush()
            if row.get("paid"):
                db.add(Payment(expense_id=expense.id, amount=expense.amount, scheduled_date=when or date.today(), status="PAID",
                               reference=row.get("reference") or f"planilha {batch.filename} linha {row['line']}", created_by=subject,
                               confirmed_by=subject))
        else:
            if not row.get("service_id") or db.scalar(select(ServiceItem.project_id).where(ServiceItem.id == row["service_id"])) != pid:
                skipped += 1
                continue
            db.add(Measurement(service_item_id=row["service_id"], quantity=Decimal(row["quantity"]), status="PENDING",
                               recorded_by=subject, measured_on=when or date.today(), notes=(row.get("notes") or f"planilha {batch.filename}")[:500]))
        created += 1
    batch.status = "COMMITTED"
    batch.committed_at = datetime.now(timezone.utc)
    db.add(AuditEvent(organization_id=batch.organization_id, subject_id=subject, action=f"import.commit:{created}", resource_id=batch.id))
    db.commit()
    return {"id": batch.id, "created": created, "skipped": skipped, "kind": batch.kind}
