import pytest
from app.full_finance_policy import (
    FinancialEligibility, Operation, PaymentGateError, Plan, require_payment_eligibility
)


def eligible(**overrides):
    data = dict(plan=Plan.FULL, organization_verified=True,
                provider_charges_enabled=True, provider_payouts_enabled=True,
                provider_global_payouts_approved=True, contract_reconciled=True,
                recipient_verified=True, finance_approved=True)
    data.update(overrides)
    return FinancialEligibility(**data)


@pytest.mark.parametrize("overrides", [
    {"plan": Plan.PROFESSIONAL},
    {"organization_verified": False},
    {"provider_payouts_enabled": False},
    {"provider_global_payouts_approved": False},
    {"contract_reconciled": False},
    {"recipient_verified": False},
    {"finance_approved": False},
])
def test_supplier_payout_fails_closed(overrides):
    with pytest.raises(PaymentGateError):
        require_payment_eligibility(Operation.SUPPLIER_PAYOUT, "100.00", eligible(**overrides))


def test_receive_requires_charges_enabled():
    with pytest.raises(PaymentGateError):
        require_payment_eligibility(Operation.RECEIVE, "1.00", eligible(provider_charges_enabled=False))


@pytest.mark.parametrize("amount", ["0", "-1", "NaN", "Infinity", "1.001", "invalid"])
def test_invalid_amounts_blocked(amount):
    with pytest.raises(PaymentGateError):
        require_payment_eligibility(Operation.RECEIVE, amount, eligible())


def test_valid_amount_is_decimal_and_no_money_is_moved():
    assert require_payment_eligibility(Operation.RECEIVE, "15.5", eligible()).as_tuple().exponent == -2
    assert require_payment_eligibility(Operation.SUPPLIER_PAYOUT, "99.99", eligible()) == 99.99
