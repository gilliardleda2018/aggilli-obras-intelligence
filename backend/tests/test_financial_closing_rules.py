import pytest
from decimal import Decimal
from app.financial_closing_rules import (
    FinancialValidationError, calculate_settlement, may_close_period
)


def test_partial_payment_and_retention():
    s = calculate_settlement(gross="1000.00", withheld="110.00",
                             advances_applied="200.00", additions="10.00",
                             payments=("300.00", "100.00"))
    assert s.net_due == Decimal("700.00")
    assert s.paid == Decimal("400.00")
    assert s.remaining == Decimal("300.00")


def test_full_settlement_without_provider():
    s = calculate_settlement(gross="100", payments=("40", "60"))
    assert s.remaining == Decimal("0.00")


@pytest.mark.parametrize("kwargs", [
    {"gross": "100", "payments": ("101",)},
    {"gross": "100", "withheld": "80", "advances_applied": "21"},
    {"gross": "100", "payments": ("-1",)},
    {"gross": "NaN"},
    {"gross": "Infinity"},
    {"gross": "10.001"},
    {"gross": "0"},
])
def test_invalid_settlement_is_rejected(kwargs):
    with pytest.raises(FinancialValidationError):
        calculate_settlement(**kwargs)


def test_period_close_requires_all_gates():
    assert may_close_period(unreconciled_contracts=0, pending_bank_items=0,
                            unsupported_settlements=0, duplicate_items=0)
    for field in ("unreconciled_contracts", "pending_bank_items",
                  "unsupported_settlements", "duplicate_items"):
        args = dict(unreconciled_contracts=0, pending_bank_items=0,
                    unsupported_settlements=0, duplicate_items=0)
        args[field] = 1
        assert not may_close_period(**args)
