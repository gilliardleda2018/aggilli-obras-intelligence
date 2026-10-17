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

def test_non_dict_item_does_not_crash_consistency_check():
    assert ocr.problems({"kind": "RECIBO", "confidence": "high",
                         "total_amount": 10, "items": [None, {"total": 10}]}) == []


def test_missing_sdk_returns_manual_fallback(monkeypatch):
    import builtins
    monkeypatch.setenv("DOC_AI_PROVIDER", "anthropic")
    original = builtins.__import__
    def no_sdk(name, *args, **kwargs):
        if name == "anthropic":
            raise ImportError("not installed")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_sdk)
    with pytest.raises(ocr.ExtractionUnavailable):
        ocr._client()

def test_aws_provider_requires_workspace(monkeypatch):
    import sys
    monkeypatch.setenv("DOC_AI_PROVIDER", "aws")
    monkeypatch.delenv("ANTHROPIC_AWS_WORKSPACE_ID", raising=False)
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(AnthropicAWS=lambda **kwargs: object()))
    with pytest.raises(ocr.ExtractionUnavailable, match="Workspace"):
        ocr._client()


def test_direct_provider_requires_key(monkeypatch):
    import sys
    monkeypatch.setenv("DOC_AI_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=lambda **kwargs: object()))
    with pytest.raises(ocr.ExtractionUnavailable, match="Chave"):
        ocr._client()


def test_sdk_provider_symbols_when_installed():
    """Runtime contract check: CI installs the declared official Anthropic dependency."""
    import anthropic
    assert callable(getattr(anthropic, "AnthropicAWS", None)), "AnthropicAWS missing from installed SDK"
    assert callable(getattr(anthropic, "AnthropicBedrockMantle", None)), "AnthropicBedrockMantle missing from installed SDK"
    assert callable(getattr(anthropic, "Anthropic", None)), "Anthropic client missing from installed SDK"


def test_sdk_aws_constructor_signature():
    """Ensure AWS client exposes the timeout argument used by OCR without network calls."""
    import inspect
    import anthropic
    signature = inspect.signature(anthropic.AnthropicAWS)
    assert "timeout" in signature.parameters


def test_sdk_bedrock_constructor_signature():
    """Check Bedrock Mantle constructor contract without invoking a model."""
    import inspect
    import anthropic
    signature = inspect.signature(anthropic.AnthropicBedrockMantle)
    assert "aws_region" in signature.parameters
    assert "timeout" in signature.parameters


def test_textract_adapter_uses_existing_contract_without_network(monkeypatch):
    import sys
    fake_response = {"ExpenseDocuments": [{"SummaryFields": [
        {"Type": {"Text": "VENDOR_NAME"}, "ValueDetection": {"Text": "Materiais Exemplo", "Confidence": 99}},
        {"Type": {"Text": "TOTAL"}, "ValueDetection": {"Text": "R$ 1.234,56", "Confidence": 99}}
    ], "LineItemGroups": []}]}
    class Client:
        def analyze_expense(self, **kwargs):
            assert kwargs["Document"]["Bytes"] == b"synthetic"
            return fake_response
    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=lambda *args, **kwargs: Client()))
    monkeypatch.setenv("DOC_AI_PROVIDER", "textract")
    result = ocr.extract(b"synthetic")
    assert result["engine"] == "amazon-textract-analyze-expense"
    assert result["fields"]["supplier_name"] == "Materiais Exemplo"
    assert result["fields"]["total_amount"] == 1234.56
    assert result["key"] is None


def test_textract_brazilian_receipt_fields_and_fractional_items(monkeypatch):
    import sys
    summary = [
        ("VENDOR_NAME", "SUPERMERCADO EXEMPLO LTDA"),
        ("TOTAL", "85,50"),
        ("INVOICE_RECEIPT_DATE", "16/10/2026"),
        ("INVOICE_RECEIPT_ID", "000123456"),
        ("OTHER", "12.345.678/0001-90"),
        ("OTHER", "Cartão de Débito"),
    ]
    lines = [("ARROZ TIPO 1 5KG", "1", "UN", "28,90"),
             ("FEIJÃO CARIOCA 1KG", "2", "UN", "17,00"),
             ("ÓLEO DE SOJA 900ML", "1", "UN", "7,90"),
             ("LEITE INTEGRAL 1L", "3", "UN", "14,97"),
             ("PÃO FRANCÊS KG", "0,5 KG", "", "8,45"),
             ("BANANA PRATA KG", "1,2", "KG", "8,28")]
    def field(t, v):
        return {"Type": {"Text": t}, "ValueDetection": {"Text": v, "Confidence": 99}}
    response = {"ExpenseDocuments": [{"SummaryFields": [field(t, v) for t, v in summary],
        "LineItemGroups": [{"LineItems": [{"LineItemExpenseFields": [
            field("ITEM", name), field("QUANTITY", qty), field("UNIT", unit), field("TOTAL", price)
        ]} for name, qty, unit, price in lines]}]}]}
    class Client:
        def analyze_expense(self, **kwargs):
            assert kwargs["Document"]["Bytes"] == b"synthetic"
            return response
    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=lambda *args, **kwargs: Client()))
    monkeypatch.setenv("DOC_AI_PROVIDER", "textract")
    result = ocr.extract(b"synthetic")
    fields = result["fields"]
    assert fields["supplier_name"] == "SUPERMERCADO EXEMPLO LTDA"
    assert fields["supplier_cnpj"] == "12.345.678/0001-90"
    assert fields["issue_date"] == "2026-10-16"
    assert fields["document_number"] == "000123456"
    assert fields["payment_method"] == "Cartão de Débito"
    assert fields["total_amount"] == 85.50
    assert len(fields["items"]) == 6
    assert fields["items"][4]["quantity"] == 0.5
    assert fields["items"][4]["unit"] == "KG"
    assert sum(item["total"] for item in fields["items"]) == 85.50
    assert result["problems"] == []


def test_textract_invalid_date_is_not_invented():
    assert ocr._textract_date("31/02/2026") is None
    assert ocr._textract_date("16/10/2026") == "2026-10-16"


def test_textract_invalid_money_is_not_invented():
    assert ocr._textract_money("R$ 1.234,56") == 1234.56
    assert ocr._textract_money("ilegível") is None


def test_textract_ambiguous_unit_price_does_not_become_line_total(monkeypatch):
    import sys
    def f(t, v):
        return {"Type": {"Text": t}, "ValueDetection": {"Text": v, "Confidence": 98}}
    response = {"ExpenseDocuments": [{"SummaryFields": [f("TOTAL", "17,00")],
        "LineItemGroups": [{"LineItems": [{"LineItemExpenseFields": [
            f("ITEM", "FEIJÃO"), f("QUANTITY", "2"), f("PRICE", "8,50")]}]}]}]}
    class Client:
        def analyze_expense(self, **kwargs):
            return response
    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=lambda *args, **kwargs: Client()))
    monkeypatch.setenv("DOC_AI_PROVIDER", "textract")
    result = ocr.extract(b"synthetic")
    assert result["fields"]["items"][0]["total"] is None
    assert result["fields"]["total_amount"] == 17.0
