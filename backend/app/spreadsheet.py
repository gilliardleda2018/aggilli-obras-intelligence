"""Read CSV/XLSX spreadsheets the way people actually write them (Brazilian formats, extra title rows, merged notes)."""
import csv
import difflib
import io
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from .classifier import normalize

MAX_ROWS = 5000
# Column synonyms (normalized). The first header row matching at least two fields is used.
FIELDS = {
    "date": ["data", "dia", "data da despesa", "data do lancamento", "data da medicao", "vencimento", "data pagamento", "competencia"],
    "project": ["obra", "obras", "projeto", "local", "frente", "centro de custo", "servicos"],
    "supplier": ["fornecedor", "empreiteiro", "favorecido", "prestador", "nome", "credor", "beneficiario", "equipe"],
    "description": ["descricao", "historico", "servico", "item", "material", "atividade", "detalhe", "especificacao", "obs servico"],
    "amount": ["valor", "valor total", "total", "valor r$", "r$", "valor pago", "folha", "custo", "montante", "programado"],
    "category": ["categoria", "tipo", "natureza", "classificacao", "grupo"],
    "status": ["situacao", "status", "pago", "pagamento"],
    "reference": ["comprovante", "nota", "nf", "documento", "referencia", "recibo"],
    "notes": ["observacao", "observacoes", "obs", "nota interna"],
    "quantity": ["quantidade", "qtd", "qtde", "medido", "executado", "quant"],
    "unit": ["unidade", "un", "und"],
}
CATEGORY_WORDS = {"material": "MATERIAL", "materiais": "MATERIAL", "mao de obra": "LABOR", "folha": "LABOR", "combustivel": "FUEL",
                  "equipamento": "EQUIPMENT", "equipamentos": "EQUIPMENT", "servico": "SERVICE", "servicos": "SERVICE", "outros": "OTHER"}


def read_table(content: bytes, filename: str) -> list[list]:
    if filename.lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        book = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = book.worksheets[0]
        rows = [list(row) for row in sheet.iter_rows(values_only=True)]
        book.close()
        return rows[:MAX_ROWS + 20]
    text = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    # Brazilian spreadsheets use ";" (the comma is the decimal separator); then tab; then comma.
    head = text[:8192]
    delimiter = ";" if ";" in head else "\t" if "\t" in head else ","
    return [row for row in csv.reader(io.StringIO(text), delimiter=delimiter)][:MAX_ROWS + 20]


def detect_header(rows: list[list]) -> tuple[int, dict[str, int]]:
    best = (-1, {})
    for index, row in enumerate(rows[:15]):
        mapping: dict[str, int] = {}
        for col, cell in enumerate(row):
            name = normalize(str(cell or ""))
            if not name:
                continue
            for field, synonyms in FIELDS.items():
                if field not in mapping and (name in synonyms or any(name.startswith(s + " ") for s in synonyms)):
                    mapping[field] = col
                    break
        if len(mapping) > len(best[1]):
            best = (index, mapping)
    return best


def parse_money(value) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value)).quantize(Decimal("0.01"))
    text = re.sub(r"[^\d,.\-]", "", str(value))
    if not text or text in "-.,":
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def parse_quantity(value) -> Decimal | None:
    amount = parse_money(value) if not isinstance(value, (int, float)) else Decimal(str(value))
    return None if amount is None else Decimal(str(amount)).quantize(Decimal("0.001"))


def parse_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and 20000 < value < 80000:  # Excel serial date
        return date(1899, 12, 30) + timedelta(days=int(value))
    text = str(value).strip()
    for pattern in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def match_project(name: str, projects: dict[str, str]) -> tuple[str | None, float]:
    """Best project id for a free-text name (accent/case-insensitive, partial names allowed)."""
    target = normalize(name)
    if not target:
        return None, 0.0
    best_id, best_score = None, 0.0
    for project_id, project_name in projects.items():
        candidate = normalize(project_name)
        score = difflib.SequenceMatcher(None, target, candidate).ratio()
        tokens = set(re.findall(r"\w+", target)) - {"mg", "de", "da", "do", "casa", "obra"}
        if tokens and tokens <= set(re.findall(r"\w+", candidate)):
            score = max(score, 0.9)
        if target in candidate or candidate in target:
            score = max(score, 0.85)
        if score > best_score:
            best_id, best_score = project_id, score
    return (best_id, round(best_score, 2)) if best_score >= 0.6 else (None, round(best_score, 2))


def category_from_text(value) -> str | None:
    return CATEGORY_WORDS.get(normalize(str(value or "")))


def is_paid(value) -> bool:
    return normalize(str(value or "")) in {"pago", "paga", "quitado", "quitada", "sim", "liquidado", "pg"}
