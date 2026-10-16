"""Document intelligence advisory; never confirms, pays, or modifies documents.

Runs on existing OCR results and documented provenance, not new OCR calls.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .documents import _orgs
from .models import FieldDocument
from .security import require_identity

router = APIRouter(prefix="/api/v1", tags=["document-auditor"])
READ_ROLES = ["OWNER", "ADMIN", "ENGINEER", "INSPECTOR", "FIELD_OPERATOR", "VIEWER"]


def assess(document: FieldDocument) -> dict:
    """Deterministic evidence-backed findings, no mutations."""
    import json
    read = json.loads(document.extraction) if document.extraction else {}
    fields = read.get("fields") or {}
    problems = read.get("problems") or []
    findings = []
    def add(code, severity, message, action, evidence):
        findings.append({"code": code, "severity": severity, "message": message,
                         "recommended_action": action, "evidence": evidence})
    if document.extraction_error:
        add("OCR_UNAVAILABLE", "warning", "Leitura automática indisponível.",
            "Conferir o documento original manualmente.",
            {"engine": document.extraction_engine, "read_error": document.extraction_error})
    elif not document.extraction:
        add("OCR_NOT_AVAILABLE", "info", "Documento sem extração automática.",
            "Conferir o original e preencher os campos manualmente.",
            {"sha256": document.sha256})
    for issue in problems:
        add("OCR_REVIEW_REQUIRED", "warning", "A extração apresentou uma inconsistência.",
            "Comparar com o arquivo original antes de confirmar.",
            {"issue": str(issue)[:300], "engine": document.extraction_engine})
    if not fields.get("supplier_name"):
        add("SUPPLIER_MISSING", "info", "Fornecedor não identificado na extração.",
            "Identificar fornecedor no documento original.",
            {"sha256": document.sha256})
    if fields.get("total_amount") is None:
        add("AMOUNT_MISSING", "info", "Valor total não identificado na extração.",
            "Conferir valor e moeda no documento original.",
            {"sha256": document.sha256})
    if document.project_id is None:
        add("PROJECT_NOT_CONFIRMED", "warning", "Obra ainda não confirmada.",
            "Confirmar manualmente a obra de destino.",
            {"suggested_project_id": document.suggested_project_id,
             "suggestion_reason": document.suggestion_reason})
    if document.status == "CONFIRMED":
        add("ALREADY_CONFIRMED", "info", "Documento já confirmado por usuário.",
            "Consultar o lançamento existente antes de qualquer ajuste.",
            {"expense_id": document.expense_id})
    if not findings:
        add("READY_FOR_HUMAN_REVIEW", "info", "Nenhuma pendência adicional identificada nas regras atuais.",
            "Revisar o original antes de confirmar.",
            {"sha256": document.sha256, "engine": document.extraction_engine})
    order = {"warning": 0, "info": 1}
    findings.sort(key=lambda f: (order[f["severity"]], f["code"], str(f["evidence"])))
    return {"document_id": document.id, "status": document.status,
            "source_sha256": document.sha256, "findings": findings}


@router.get("/document-auditor/diagnosis")
def document_diagnosis(subject: str = Depends(require_identity), db: Session = Depends(get_db)):
    orgs = _orgs(db, subject, READ_ROLES)
    if not orgs:
        return {"agent": "auditor-documental-ia", "version": "1.0", "mode": "advisory",
                "documents": [], "writes_performed": False}
    docs = db.scalars(select(FieldDocument).where(FieldDocument.organization_id.in_(orgs))
                      .order_by(FieldDocument.created_at.desc()).limit(100)).all()
    return {"agent": "auditor-documental-ia", "version": "1.0", "mode": "advisory",
            "documents": [assess(d) for d in docs], "writes_performed": False}
