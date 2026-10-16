"""Fail-closed business policy for Aggilli Obras Full payment workflows.

Pure domain module: no Stripe calls, no secrets, no money movement.
Provider eligibility is not equivalent to an organization having a paid Full license.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum


class PaymentGateError(ValueError):
    pass


class Plan(str, Enum):
    PROFESSIONAL = "PROFESSIONAL"
    FULL = "FULL"


class Operation(str, Enum):
    RECEIVE = "RECEIVE"
    SUPPLIER_PAYOUT = "SUPPLIER_PAYOUT"


@dataclass(frozen=True)
class FinancialEligibility:
    plan: Plan
    organization_verified: bool
    provider_charges_enabled: bool
    provider_payouts_enabled: bool
    provider_global_payouts_approved: bool
    contract_reconciled: bool
    recipient_verified: bool
    finance_approved: bool


def require_payment_eligibility(operation: Operation, amount: str, state: FinancialEligibility) -> Decimal:
    """Validate authorization prerequisites; never execute or schedule a payment."""
    try:
        value = Decimal(amount)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PaymentGateError("Valor inválido") from exc
    if not value.is_finite() or value <= 0 or value.as_tuple().exponent < -2:
        raise PaymentGateError("Valor monetário inválido")
    if state.plan != Plan.FULL:
        raise PaymentGateError("Módulo financeiro Full não habilitado")
    if not state.organization_verified:
        raise PaymentGateError("Organização não verificada")
    if operation == Operation.RECEIVE:
        if not state.provider_charges_enabled:
            raise PaymentGateError("Cobranças Stripe não habilitadas")
    elif operation == Operation.SUPPLIER_PAYOUT:
        if not (state.provider_payouts_enabled and state.provider_global_payouts_approved):
            raise PaymentGateError("Global Payouts não aprovado para esta conta")
        if not state.contract_reconciled:
            raise PaymentGateError("Saldo contratual pendente de conciliação")
        if not state.recipient_verified:
            raise PaymentGateError("Destinatário não verificado")
        if not state.finance_approved:
            raise PaymentGateError("Pagamento não aprovado pelo financeiro")
    else:
        raise PaymentGateError("Operação desconhecida")
    return value.quantize(Decimal("0.01"))
