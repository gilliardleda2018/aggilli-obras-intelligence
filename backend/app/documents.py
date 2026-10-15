"""Field documents: photograph a receipt, invoice or quote on site → OCR suggests the values → a person confirms.

The work is suggested from where the picture was taken (camera EXIF or phone GPS) compared with the confirmed location
of every work of the organization, using the same radius as the work diary. It is always shown as a suggestion with
its reason; nothing becomes an expense until someone confirms work, supplier and amount.
"""
import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import ocr, storage
from .classifier import CATEGORIES, Classifier
from .db import get_db
from .diary import FORMATS, LOCAL_TZ, MAX_ACCURACY_MARGIN_M, SITE_RADIUS_M, _in_brazil, _local, distance_m, read_exif, read_image
from .measurements import access
from .models import AuditEvent, Expense, FieldDocument, Membership, Payment, Project
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["documents"])
READ_ROLES = ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "FIELD_OPERATOR", "VIEWER"]
WRITE_ROLES = ["OWNER", "ADMIN", "ENGINEER", "FIELD_OPERATOR"]
KIND_LABEL = {"NOTA_FISCAL": "Nota fiscal", "RECIBO": "Recibo", "ORCAMENTO": "Orçamento", "COMPROVANTE": "Comprovante",
              "OUTRO": "Documento"}


def _orgs(db: Session, subject: str, roles: list[str]) -> list[str]:
    return list(db.scalars(select(Membership.organization_id).where(Membership.subject_id == subject, Membership.role.in_(roles))).all())


def _document(db: Session, subject: str, document_id: str, roles: list[str]) -> FieldDocument:
    document = db.get(FieldDocument, document_id)
    if not document or document.organization_id not in _orgs(db, subject, roles):
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return document


def match_site(projects: list[Project], latitude: float, longitude: float, accuracy: float | None) -> tuple[Project | None, str]:
    """The work this position falls in, or why none was picked."""
    located = [(round(distance_m(latitude, longitude, float(p.latitude), float(p.longitude))), p)
               for p in projects if p.latitude is not None and p.longitude is not None and p.status != "COST_POOL"]
    if not located:
        return None, "Nenhuma obra com localização confirmada para comparar"
    radius = SITE_RADIUS_M + min(accuracy or 0, MAX_ACCURACY_MARGIN_M)
    near = sorted((item for item in located if item[0] <= radius), key=lambda item: item[0])
    if len(near) == 1:
        return near[0][1], f"Fotografado na obra (GPS, a {near[0][0]} m)"
    if near:
        return near[0][1], f"Mais próxima entre {len(near)} obras no raio do GPS (a {near[0][0]} m) — confira"
    meters, closest = min(located, key=lambda item: item[0])
    where = f"{meters} m" if meters < 1000 else f"{meters / 1000:.1f} km".replace(".", ",")
    return None, f"Fotografado fora das obras (a mais próxima, {closest.name}, fica a {where})"


def _draft(document: FieldDocument, read: dict | None, classifier: Classifier | None) -> dict:
    """Values to pre-fill the confirmation form."""
    fields = (read or {}).get("fields") or {}
    key = (read or {}).get("key")
    items = [item.get("description") for item in fields.get("items") or [] if item.get("description")]
    supplier = fields.get("supplier_name") or ""
    description = "; ".join(items)[:300] if items else (KIND_LABEL.get(document.kind or "", "Documento")
                                                       + (" " + fields["document_number"] if fields.get("document_number") else ""))
    suggestion = classifier.suggest(f"{supplier} {' '.join(items)}") if classifier and (supplier or items) else None
    issue = fields.get("issue_date")
    try:
        issue = date.fromisoformat(issue).isoformat() if issue else None
    except ValueError:
        issue = None
    return {"supplier": supplier[:200], "supplier_cnpj": fields.get("supplier_cnpj") or (key or {}).get("cnpj"),
            "description": description, "amount": str(ocr._money(fields.get("total_amount")) or "") or None,
            "expense_date": issue, "document_number": fields.get("document_number") or (key or {}).get("number"),
            "category": suggestion["category"] if suggestion else None, "category_reason": suggestion["reason"] if suggestion else None,
            "items": fields.get("items") or [], "site_reference": fields.get("site_reference"),
            "confidence": fields.get("confidence"), "issues": fields.get("issues") or []}


def document_json(db: Session, document: FieldDocument, classifier: Classifier | None = None) -> dict:
    names = dict(db.execute(select(Project.id, Project.name).where(Project.organization_id == document.organization_id)).all())
    read = json.loads(document.extraction) if document.extraction else None
    return {"id": document.id, "status": document.status, "kind": document.kind, "kind_label": KIND_LABEL.get(document.kind or ""),
            "url": "/documents/" + document.id + "/file", "width": document.width, "height": document.height,
            "project_id": document.project_id, "project": names.get(document.project_id or ""),
            "suggested_project_id": document.suggested_project_id, "suggested_project": names.get(document.suggested_project_id or ""),
            "suggestion_reason": document.suggestion_reason,
            "latitude": float(document.latitude) if document.latitude is not None else None,
            "longitude": float(document.longitude) if document.longitude is not None else None,
            "location_source": document.location_source, "access_key": document.access_key,
            "nfe": (read or {}).get("key"), "engine": document.extraction_engine, "read_error": document.extraction_error,
            "problems": (read or {}).get("problems") or [], "draft": _draft(document, read, classifier),
            "expense_id": document.expense_id, "recorded_by": document.recorded_by, "created_at": _local(document.created_at).isoformat(),
            "taken_at": _local(document.taken_at).isoformat() if document.taken_at else None,
            "confirmed_by": document.confirmed_by}


def _classifier(db: Session, organization_id: str) -> Classifier:
    samples = db.execute(select(Expense.supplier, Expense.description, Expense.category).join(Project, Project.id == Expense.project_id)
                         .where(Project.organization_id == organization_id).limit(5000)).all()
    return Classifier([(f"{supplier} {description}", category) for supplier, description, category in samples])


@router.post("/documents", status_code=201)
async def upload_document(file: UploadFile = File(...), organization_id: str | None = Form(None), project_id: str | None = Form(None),
                          latitude: float | None = Form(None), longitude: float | None = Form(None), accuracy: float | None = Form(None),
                          taken_at: datetime | None = Form(None),
                          subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    chosen = access(db, subject, project_id, WRITE_ROLES) if project_id else None
    orgs = _orgs(db, subject, WRITE_ROLES)
    if chosen:
        organization_id = chosen.organization_id
    elif organization_id not in orgs:
        if organization_id or not orgs:
            raise HTTPException(status_code=404, detail="Organização não encontrada")
        organization_id = orgs[0]
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="Latitude e longitude devem vir juntas")
    if latitude is not None and not _in_brazil(latitude, longitude):
        raise HTTPException(status_code=422, detail="Posição do aparelho fora do Brasil")
    if accuracy is not None and not 0 <= accuracy <= 100_000:
        raise HTTPException(status_code=422, detail="Precisão inválida")

    data, image = await read_image(file)
    digest = hashlib.sha256(data).hexdigest()
    if db.scalar(select(FieldDocument.id).where(FieldDocument.organization_id == organization_id, FieldDocument.sha256 == digest)):
        raise HTTPException(status_code=409, detail="Este documento já foi enviado")
    content_type, ext = FORMATS[image.format]
    exif = read_exif(image)
    document = FieldDocument(organization_id=organization_id, storage_key="", content_type=content_type, size_bytes=len(data),
                             sha256=digest, width=image.width, height=image.height, recorded_by=subject, status="PENDING")
    if "latitude" in exif:
        document.latitude, document.longitude, document.location_source = Decimal(str(exif["latitude"])), Decimal(str(exif["longitude"])), "EXIF"
    elif latitude is not None:
        document.latitude, document.longitude, document.location_source = Decimal(f"{latitude:.6f}"), Decimal(f"{longitude:.6f}"), "DEVICE"
        document.accuracy_m = Decimal(f"{accuracy:.1f}") if accuracy is not None else None
    moment = exif.get("taken_at") or taken_at
    if moment is not None:
        document.taken_at = (moment if moment.tzinfo else moment.replace(tzinfo=LOCAL_TZ)).astimezone(timezone.utc)

    if chosen:
        document.suggested_project_id, document.suggestion_reason = chosen.id, "Obra escolhida por quem enviou"
    elif document.latitude is not None:
        projects = list(db.scalars(select(Project).where(Project.organization_id == organization_id)).all())
        site, reason = match_site(projects, float(document.latitude), float(document.longitude),
                                  float(document.accuracy_m) if document.accuracy_m is not None else None)
        document.suggested_project_id, document.suggestion_reason = (site.id if site else None), reason
    else:
        document.suggestion_reason = "Sem localização: escolha a obra"

    try:
        read = await run_in_threadpool(ocr.extract, data)  # network call: keep the event loop free
    except ocr.ExtractionUnavailable:
        read = None
    except ocr.ExtractionFailed as error:
        read, document.extraction_error = None, str(error)[:300]
    if read:
        if read["key"]:
            other = db.scalar(select(FieldDocument.id).where(FieldDocument.organization_id == organization_id, FieldDocument.status != "DISCARDED",
                                                            FieldDocument.access_key == read["key"]["access_key"]))
            if other:
                read["problems"].append("esta nota fiscal já foi enviada em outro documento")
            document.access_key = read["key"]["access_key"]
        document.kind = read["fields"].get("kind") if read["fields"].get("kind") in ocr.KINDS else None
        document.extraction, document.extraction_engine = json.dumps(read, ensure_ascii=False), read["engine"]

    db.add(document)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Este documento já foi enviado")
    document.storage_key = f"documents/{document.id}.{ext}"
    storage.save(document.storage_key, data, content_type)
    db.add(AuditEvent(organization_id=organization_id, subject_id=subject, action="field_document.create", resource_id=document.id))
    try:
        db.commit()
    except Exception:
        storage.delete(document.storage_key)
        raise
    return document_json(db, document, _classifier(db, organization_id))


@router.get("/documents")
def list_documents(status: str = "PENDING", subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    orgs = _orgs(db, subject, READ_ROLES)
    rows = db.scalars(select(FieldDocument).where(FieldDocument.organization_id.in_(orgs), FieldDocument.status == status.upper())
                      .order_by(FieldDocument.created_at.desc()).limit(200)).all() if orgs else []
    return [document_json(db, row) for row in rows]


@router.get("/projects/{project_id}/documents")
def project_documents(project_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    project = access(db, subject, project_id, READ_ROLES)
    rows = db.scalars(select(FieldDocument).where(FieldDocument.project_id == project.id, FieldDocument.status == "CONFIRMED")
                      .order_by(FieldDocument.created_at.desc())).all()
    return [document_json(db, row) for row in rows]


@router.get("/documents/{document_id}")
def get_document(document_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    document = _document(db, subject, document_id, READ_ROLES)
    return document_json(db, document, _classifier(db, document.organization_id) if document.status == "PENDING" else None)


@router.get("/documents/{document_id}/file")
def document_file(document_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    document = _document(db, subject, document_id, READ_ROLES)
    data = storage.load(document.storage_key)
    if data is None:
        raise HTTPException(status_code=404, detail="Arquivo do documento indisponível")
    return Response(data, media_type=document.content_type, headers={"Cache-Control": "private, max-age=86400"})


class Confirm(BaseModel):
    project_id: str = Field(min_length=36, max_length=36)
    kind: str = Field(pattern="^(NOTA_FISCAL|RECIBO|ORCAMENTO|COMPROVANTE|OUTRO)$")
    supplier: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=300)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    expense_date: date | None = None
    category: str = Field(pattern="^(" + "|".join(CATEGORIES) + ")$")
    notes: str | None = Field(default=None, max_length=500)
    allow_duplicate: bool = False


@router.post("/documents/{document_id}/confirm")
def confirm(document_id: str, payload: Confirm, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    document = _document(db, subject, document_id, WRITE_ROLES)
    if document.status != "PENDING":
        raise HTTPException(status_code=409, detail="Documento já conferido")
    project = access(db, subject, payload.project_id, WRITE_ROLES)
    if project.organization_id != document.organization_id:
        raise HTTPException(status_code=404, detail="Obra não encontrada")
    if payload.expense_date and payload.expense_date > date.today():
        raise HTTPException(status_code=422, detail="Data no futuro")

    if payload.kind != "ORCAMENTO":  # a quote is filed with the work but is not money spent
        reference = f"nfe:{document.access_key}" if document.access_key else f"documento:{document.id}"
        if db.scalar(select(Expense.id).where(Expense.project_id == project.id, Expense.source_ref == reference)):
            raise HTTPException(status_code=409, detail="Esta nota já está lançada nesta obra")
        if not payload.allow_duplicate and payload.expense_date and db.scalar(select(Expense.id).where(
                Expense.project_id == project.id, Expense.amount == payload.amount, Expense.expense_date == payload.expense_date,
                func.lower(Expense.supplier) == payload.supplier.strip().lower())):
            raise HTTPException(status_code=409, detail="Já existe gasto com o mesmo fornecedor, valor e data nesta obra")
        expense = Expense(project_id=project.id, supplier=payload.supplier.strip(), description=payload.description.strip(),
                          amount=payload.amount, category=payload.category, status="OPEN", created_by=subject,
                          expense_date=payload.expense_date, notes=payload.notes, source_ref=reference, evidence_key=f"documento:{document.id}")
        db.add(expense)
        db.flush()
        if payload.kind == "COMPROVANTE":  # proof of payment: the money already left
            db.add(Payment(expense_id=expense.id, amount=expense.amount, scheduled_date=payload.expense_date or date.today(), status="PAID",
                           reference=f"comprovante {document.id}", created_by=subject, confirmed_by=subject))
        document.expense_id = expense.id
    document.project_id, document.kind, document.status = project.id, payload.kind, "CONFIRMED"
    document.confirmed_by, document.confirmed_at = subject, datetime.now(timezone.utc)
    db.add(AuditEvent(organization_id=document.organization_id, subject_id=subject, action="field_document.confirm", resource_id=document.id))
    db.commit()
    return document_json(db, document)


@router.post("/documents/{document_id}/discard")
def discard(document_id: str, subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    document = _document(db, subject, document_id, WRITE_ROLES)
    if document.status != "PENDING":
        raise HTTPException(status_code=409, detail="Documento já conferido")
    document.status = "DISCARDED"  # the file stays for the audit trail
    db.add(AuditEvent(organization_id=document.organization_id, subject_id=subject, action="field_document.discard", resource_id=document.id))
    db.commit()
    return document_json(db, document)
