"""Core BRL financial settlement arithmetic; provider-independent and side-effect free."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


class FinancialValidationError(ValueError):
    pass


CENT = Decimal("0.01")


def brl(value: str | Decimal) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise FinancialValidationError("Valor monetário inválido") from exc
    if not amount.is_finite() or amount.as_tuple().exponent < -2:
        raise FinancialValidationError("Valor monetário inválido")
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Settlement:
    gross: Decimal
    withheld: Decimal
    advances_applied: Decimal
    additions: Decimal
    net_due: Decimal
    paid: Decimal
    remaining: Decimal


def calculate_settlement(*, gross: str, withheld: str = "0", advances_applied: str = "0",
                         additions: str = "0", payments: tuple[str, ...] = ()) -> Settlement:
    """Amounts are explicitly supplied/approved, never inferred from tax rates."""
    g, w, a, extra = (brl(v) for v in (gross, withheld, advances_applied, additions))
    if g <= 0 or min(w, a, extra) < 0:
        raise FinancialValidationError("Valor bruto deve ser positivo e deduções não negativas")
    if w + a > g:
        raise FinancialValidationError("Retenções e adiantamentos excedem o valor bruto")
    due = g - w - a + extra
    amounts = tuple(brl(p) for p in payments)
    if any(p <= 0 for p in amounts):
        raise FinancialValidationError("Pagamentos devem ser positivos")
    paid = sum(amounts, Decimal("0.00"))
    if paid > due:
        raise FinancialValidationError("Pagamento excede obrigação líquida")
    return Settlement(g, w, a, extra, due, paid, due - paid)


def may_close_period(*, unreconciled_contracts: int, pending_bank_items: int,
                     unsupported_settlements: int, duplicate_items: int) -> bool:
    counters = (unreconciled_contracts, pending_bank_items, unsupported_settlements, duplicate_items)
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in counters):
        raise FinancialValidationError("Contadores de fechamento inválidos")
    return all(v == 0 for v in counters)
