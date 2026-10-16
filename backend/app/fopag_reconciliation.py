"""FOPAG contract reconciliation: works without any payment provider.

A mismatch is a review item, never an automatic adjustment or bank payment.
"""
from decimal import Decimal
from typing import Any


def money(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"))


def reconcile_contracts(contracts: list[dict], declared: dict[str, str] | None = None) -> dict:
    lines = []
    totals = {"contracted": Decimal("0"), "advances": Decimal("0"), "reported_balance": Decimal("0")}
    for index, row in enumerate(contracts, start=1):
        total, advance, balance = money(row.get("total")), money(row.get("advance")), money(row.get("balance"))
        if advance is not None:
            totals["advances"] += advance
        if balance is not None:
            totals["reported_balance"] += balance
        if total is not None:
            totals["contracted"] += total
        expected = None if total is None or advance is None else total - advance
        issues = []
        if total is None:
            issues.append("CONTRACT_VALUE_MISSING")
        if advance is None or balance is None:
            issues.append("FINANCIAL_VALUE_MISSING")
        if expected is not None and balance is not None and expected != balance:
            issues.append("BALANCE_MISMATCH")
        lines.append({"line": index, "contractor": row.get("name"), "project": row.get("project"),
                      "contracted": None if total is None else str(total),
                      "advance": None if advance is None else str(advance),
                      "reported_balance": None if balance is None else str(balance),
                      "calculated_balance": None if expected is None else str(expected),
                      "difference": None if expected is None or balance is None else str(expected - balance),
                      "issues": issues, "reconciled": not issues})
    summary = {k: str(v) for k, v in totals.items()}
    document_issues = []
    for key, value in (declared or {}).items():
        if key in totals and money(value) != totals[key]:
            document_issues.append({"field": key, "declared": str(money(value)),
                                    "sum_of_lines": str(totals[key]), "difference": str(totals[key] - money(value))})
    return {"rows": lines, "summary": summary, "document_issues": document_issues,
            "ready_for_financial_close": not document_issues and all(x["reconciled"] for x in lines),
            "provider": "MANUAL", "money_moved": False}
