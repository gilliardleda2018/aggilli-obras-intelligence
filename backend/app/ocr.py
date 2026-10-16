"""Reading receipts, invoices and quotes photographed on site.

Two sources, never mixed silently:
- the 44-digit access key of an electronic invoice (NF-e / NFC-e), trusted only when its check digit matches;
- Claude reading the picture (DOC_AI_PROVIDER), first with a cheap model and, when the result does not add up
  (low confidence, items not matching the total, invalid key), once more with a stronger one.
Whatever comes out is a suggestion: a person confirms every value before it becomes an expense.
"""
import base64
import io
import json
import os
import re
from decimal import Decimal, InvalidOperation

from PIL import Image, ImageOps

KINDS = ("NOTA_FISCAL", "RECIBO", "ORCAMENTO", "COMPROVANTE", "OUTRO")
MAX_SIDE = 1600  # enough to read small print; keeps a photo near 2.5k image tokens
UF = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
      "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
      "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}


class ExtractionUnavailable(Exception):
    """Reading is switched off or not configured; the document is filled in by hand."""


class ExtractionFailed(Exception):
    pass


# --- NF-e / NFC-e access key -------------------------------------------------------------------------------------

def access_key_digit(first43: str) -> int:
    total, weight = 0, 2
    for digit in reversed(first43):
        total += int(digit) * weight
        weight = 2 if weight == 9 else weight + 1
    rest = total % 11
    return 0 if rest < 2 else 11 - rest


def parse_access_key(text: str | None) -> dict | None:
    """The fields encoded in a valid access key; None when it is not 44 digits or the check digit fails."""
    digits = re.sub(r"\D", "", text or "")
    if len(digits) != 44 or access_key_digit(digits[:43]) != int(digits[43]) or digits[0:2] not in UF:
        return None
    year, month = 2000 + int(digits[2:4]), int(digits[4:6])
    if not 1 <= month <= 12:
        return None
    cnpj = digits[6:20]
    return {"access_key": digits, "uf": UF[digits[0:2]], "year_month": f"{year:04d}-{month:02d}",
            "cnpj": f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}",
            "model": {"55": "NF-e", "65": "NFC-e"}.get(digits[20:22], digits[20:22]),
            "series": str(int(digits[22:25])), "number": str(int(digits[25:34]))}


# --- Claude ------------------------------------------------------------------------------------------------------

NULLABLE_STRING = {"anyOf": [{"type": "string"}, {"type": "null"}]}
NULLABLE_NUMBER = {"anyOf": [{"type": "number"}, {"type": "null"}]}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["kind", "supplier_name", "supplier_cnpj", "document_number", "access_key", "issue_date", "total_amount",
                 "items", "payment_method", "site_reference", "confidence", "issues"],
    "properties": {
        "kind": {"type": "string", "enum": list(KINDS)},
        "supplier_name": NULLABLE_STRING, "supplier_cnpj": NULLABLE_STRING, "document_number": NULLABLE_STRING,
        "access_key": NULLABLE_STRING, "issue_date": NULLABLE_STRING, "total_amount": NULLABLE_NUMBER,
        "items": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["description", "quantity", "unit", "total"],
            "properties": {"description": {"type": "string"}, "quantity": NULLABLE_NUMBER, "unit": NULLABLE_STRING,
                           "total": NULLABLE_NUMBER}}},
        "payment_method": NULLABLE_STRING, "site_reference": NULLABLE_STRING,
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "issues": {"type": "array", "items": {"type": "string"}},
    },
}
PROMPT = """Você recebe a foto de um documento de despesa de uma obra no Brasil (nota fiscal, cupom, recibo, orçamento ou
comprovante de pagamento). Extraia somente o que está escrito; nunca invente nem complete valores.

- kind: NOTA_FISCAL (NF-e, NFC-e, cupom fiscal, DANFE), RECIBO (inclusive manuscrito), ORCAMENTO (proposta/cotação,
  ainda não é gasto), COMPROVANTE (Pix, transferência, boleto pago) ou OUTRO.
- supplier_name e supplier_cnpj: quem emitiu/recebeu o pagamento. CNPJ ou CPF como aparece.
- access_key: os 44 dígitos da chave de acesso, se houver, só dígitos.
- issue_date: data de emissão no formato AAAA-MM-DD.
- total_amount: valor total a pagar, em reais, como número (1234.56).
- items: linhas de produtos/serviços legíveis (descrição, quantidade, unidade, total da linha).
- site_reference: nome de obra, endereço de entrega ou local citado no documento, se houver.
- confidence: low se a foto estiver ilegível, cortada ou se algum valor principal for duvidoso.
- issues: problemas encontrados, em português curto (ex.: "total ilegível", "data rasurada").
Campos que não aparecem: null."""


def _image_block(data: bytes) -> dict:
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    image.save(out, "JPEG", quality=85)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.standard_b64encode(out.getvalue()).decode()}}


def _client():
    provider = (os.environ.get("DOC_AI_PROVIDER") or "off").lower()
    if provider == "off":
        raise ExtractionUnavailable("Leitura automática desligada")
    try:
        import anthropic
    except ImportError as error:
        raise ExtractionUnavailable("SDK de leitura automática não instalado") from error
    if provider == "aws":
        workspace = os.environ.get("ANTHROPIC_AWS_WORKSPACE_ID", "").strip()
        if not workspace:
            raise ExtractionUnavailable("Workspace Claude Platform on AWS não configurado")
        return anthropic.AnthropicAWS(timeout=60), ""
    if provider == "bedrock":
        return anthropic.AnthropicBedrockMantle(aws_region=os.environ.get("AWS_REGION") or "us-east-1", timeout=60), "anthropic."
    if provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ExtractionUnavailable("Chave da API Anthropic não configurada")
        return anthropic.Anthropic(timeout=60), ""
    raise ExtractionUnavailable(f"DOC_AI_PROVIDER desconhecido: {provider}")


def _ask(client, model: str, image: dict) -> dict:
    import anthropic
    try:
        response = client.messages.create(
            model=model, max_tokens=4000, output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": [image, {"type": "text", "text": PROMPT}]}])
    except anthropic.APIConnectionError as error:
        raise ExtractionFailed("Serviço de leitura indisponível") from error
    except anthropic.APIStatusError as error:
        raise ExtractionFailed(f"Serviço de leitura respondeu {error.status_code}") from error
    except (ValueError, TypeError, AttributeError) as error:
        raise ExtractionFailed("Configuração ou resposta incompatível com o SDK de leitura") from error
    if response.stop_reason in ("refusal", "max_tokens"):
        raise ExtractionFailed("Leitura não concluída")
    text = next((block.text for block in response.content if block.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ExtractionFailed("Resposta de leitura inválida") from error


def _money(value) -> Decimal | None:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01")) if value is not None else None
    except InvalidOperation:
        return None


def problems(fields: dict) -> list[str]:
    """Checks that do not need the picture: is the reading internally consistent?"""
    found = []
    if fields.get("confidence") == "low":
        found.append("leitura com baixa confiança")
    if fields.get("access_key") and not parse_access_key(fields["access_key"]):
        found.append("chave de acesso não confere")
    total = _money(fields.get("total_amount"))
    lines = [_money(item.get("total")) for item in fields.get("items") or [] if isinstance(item, dict)]
    if total is None and fields.get("kind") != "OUTRO":
        found.append("valor total não encontrado")
    elif total is not None and lines and all(v is not None for v in lines) and abs(sum(lines) - total) > Decimal("0.05"):
        found.append(f"soma dos itens ({sum(lines)}) diferente do total ({total})")
    return found



def _textract_money(raw: str | None) -> float | None:
    """Convert BRL/US money strings without silently accepting malformed values."""
    if not raw:
        return None
    value = re.sub(r"[^0-9,.-]", "", raw.strip())
    if not value or value.count("-") or value.count(",") > 1:
        return None
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".") if value.rfind(",") > value.rfind(".") else value.replace(",", "")
    elif "," in value:
        value = value.replace(",", ".")
    try:
        amount = Decimal(value)
        return float(amount) if amount.is_finite() and amount >= 0 else None
    except InvalidOperation:
        return None


def _textract_date(raw: str | None) -> str | None:
    if not raw:
        return None
    from datetime import date
    value = raw.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value).isoformat()
        match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
        if match:
            day, month, year = map(int, match.groups())
            return date(year, month, day).isoformat()
    except ValueError:
        pass
    return None


def _textract_extract(data: bytes) -> dict:
    """AnalyzeExpense to existing OCR contract. Suggestions only; never posts expenses."""
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    try:
        response = boto3.client("textract", region_name=os.environ.get("AWS_REGION") or "us-east-1").analyze_expense(
            Document={"Bytes": data}
        )
    except (BotoCoreError, ClientError) as error:
        raise ExtractionFailed("Serviço Textract indisponível ou sem autorização") from error

    fields = {"kind": "NOTA_FISCAL", "supplier_name": None, "supplier_cnpj": None,
              "document_number": None, "access_key": None, "issue_date": None,
              "total_amount": None, "items": [], "payment_method": None,
              "site_reference": None, "confidence": "low", "issues": []}
    mapping = {"VENDOR_NAME": "supplier_name", "NAME": "supplier_name",
               "VENDOR_VAT_NUMBER": "supplier_cnpj", "INVOICE_RECEIPT_ID": "document_number",
               "INVOICE_RECEIPT_DATE": "issue_date", "TOTAL": "total_amount"}
    confidences = []
    for doc in response.get("ExpenseDocuments", []):
        for item in doc.get("SummaryFields", []):
            typ = item.get("Type", {}).get("Text", "")
            value = item.get("ValueDetection", {})
            raw = value.get("Text", "").strip()
            if not raw:
                continue
            target = mapping.get(typ)
            if target:
                if fields[target] is not None:
                    continue
                confidences.append(float(value.get("Confidence", 0)))
                if target == "total_amount":
                    fields[target] = _textract_money(raw)
                    if fields[target] is None:
                        fields["issues"].append("valor total não interpretado")
                elif target == "issue_date":
                    fields[target] = _textract_date(raw)
                    if fields[target] is None:
                        fields["issues"].append("data não interpretada")
                else:
                    fields[target] = raw
            elif typ == "OTHER":
                if not fields["supplier_cnpj"]:
                    match = re.search(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", raw)
                    if match:
                        fields["supplier_cnpj"] = match.group(0)
                if not fields["payment_method"] and re.search(r"(?i)\b(pix|d[eé]bito|cr[eé]dito|dinheiro|boleto)\b", raw):
                    fields["payment_method"] = raw
        for group in doc.get("LineItemGroups", []):
            for line in group.get("LineItems", []):
                vals = {v.get("Type", {}).get("Text"): v.get("ValueDetection", {}).get("Text")
                        for v in line.get("LineItemExpenseFields", [])}
                if not vals.get("ITEM"):
                    continue
                qty_raw = (vals.get("QUANTITY") or "").replace(",", ".").strip()
                qty_match = re.match(r"^\d+(?:\.\d+)?", qty_raw)
                qty = float(qty_match.group(0)) if qty_match else None
                unit = (vals.get("UNIT") or "").strip() or None
                if not unit and qty_match:
                    unit = qty_raw[qty_match.end():].strip() or None
                fields["items"].append({"description": vals["ITEM"], "quantity": qty,
                                        "unit": unit, "total": _textract_money(vals.get("PRICE"))})
    if not response.get("ExpenseDocuments"):
        fields["issues"].append("documento sem campos reconhecidos")
    fields["confidence"] = "medium" if confidences and min(confidences) >= 85 else "low"
    found = problems(fields)
    return {"engine": "amazon-textract-analyze-expense", "fields": fields,
            "key": None, "problems": found}


def extract(data: bytes) -> dict:
    """Fields read from the picture plus which model produced them and what still looks wrong."""
    if (os.environ.get("DOC_AI_PROVIDER") or "off").lower() == "textract":
        return _textract_extract(data)
    client, prefix = _client()
    image = _image_block(data)
    model = os.environ.get("DOC_AI_MODEL") or "claude-haiku-5-5"
    fields = _ask(client, prefix + model, image)
    review = os.environ.get("DOC_AI_REVIEW_MODEL", "claude-sonnet-5-5")
    if problems(fields) and review:
        model = review
        fields = _ask(client, prefix + review, image)
    found = problems(fields)
    key = parse_access_key(fields.get("access_key"))
    fields["access_key"] = key["access_key"] if key else None  # a key that fails its check digit is not kept
    return {"engine": model, "fields": fields, "key": key, "problems": found}
