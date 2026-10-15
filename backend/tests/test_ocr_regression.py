"""OCR-only regression checks. No network, database, UI, or AWS credentials required."""
import json
from types import SimpleNamespace

import pytest

from app import ocr


def test_provider_off_remains_safe(monkeypatch):
    monkeypatch.setenv("DOC_AI_PROVIDER", "off")
    with pytest.raises(ocr.ExtractionUnavailable):
        ocr._client()


def test_invalid_provider_is_not_silently_accepted(monkeypatch):
    monkeypatch.setenv("DOC_AI_PROVIDER", "unsupported-provider")
    with pytest.raises(ocr.ExtractionUnavailable):
        ocr._client()


def test_missing_total_requires_review():
    assert "valor total não encontrado" in ocr.problems({
        "kind": "RECIBO", "confidence": "high", "total_amount": None, "items": []
    })


def test_valid_total_does_not_trigger_review():
    assert ocr.problems({
        "kind": "RECIBO", "confidence": "high", "total_amount": 150.00,
        "items": [{"total": 150.00}]
    }) == []


def test_second_model_is_only_used_on_inconsistent_reading(monkeypatch):
    monkeypatch.setenv("DOC_AI_MODEL", "test-haiku")
    monkeypatch.setenv("DOC_AI_REVIEW_MODEL", "test-sonnet")
    monkeypatch.setattr(ocr, "_client", lambda: (object(), ""))
    monkeypatch.setattr(ocr, "_image_block", lambda data: {"type": "image"})
    calls = []
    def ask(client, model, image):
        calls.append(model)
        return {"kind": "RECIBO", "confidence": "high", "total_amount": 10.0,
                "items": [{"total": 10.0}], "access_key": None}
    monkeypatch.setattr(ocr, "_ask", ask)
    result = ocr.extract(b"synthetic")
    assert calls == ["test-haiku"]
    assert result["engine"] == "test-haiku"


def test_inconsistent_reading_escalates_once(monkeypatch):
    monkeypatch.setenv("DOC_AI_MODEL", "test-haiku")
    monkeypatch.setenv("DOC_AI_REVIEW_MODEL", "test-sonnet")
    monkeypatch.setattr(ocr, "_client", lambda: (object(), ""))
    monkeypatch.setattr(ocr, "_image_block", lambda data: {"type": "image"})
    calls = []
    def ask(client, model, image):
        calls.append(model)
        return {"kind": "RECIBO", "confidence": "low" if len(calls) == 1 else "high",
                "total_amount": 10.0, "items": [{"total": 10.0}], "access_key": None}
    monkeypatch.setattr(ocr, "_ask", ask)
    result = ocr.extract(b"synthetic")
    assert calls == ["test-haiku", "test-sonnet"]
    assert result["engine"] == "test-sonnet"
    assert result["problems"] == []
