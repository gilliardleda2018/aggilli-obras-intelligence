"""Deterministic bank-statement reconciliation suggestions; no database writes.

No fuzzy matching by account holder name: explicit bank reference and exact amount
are required for automatic suggestions, which still need a human confirmation.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from .financial_closing_rules import brl


@dataclass(frozen=True)
class BankLine:
    reference: str
    posted_on: date
    amount: Decimal


@dataclass(frozen=True)
class Obligation:
    id: str
    reference: str
    amount: Decimal
    due_on: date


def suggest_matches(lines: list[BankLine], obligations: list[Obligation]) -> dict:
    suggestions, exceptions = [], []
    used = set()
    for index, line in enumerate(lines):
        candidates = [item for item in obligations if item.id not in used
                      and item.reference and line.reference
                      and item.reference == line.reference
                      and brl(item.amount) == brl(line.amount)]
        if len(candidates) == 1:
            match = candidates[0]
            used.add(match.id)
            suggestions.append({"bank_line": index, "obligation_id": match.id,
                                "reason": "EXACT_REFERENCE_AND_AMOUNT", "status": "SUGGESTED"})
        else:
            exceptions.append({"bank_line": index, "reason": "AMBIGUOUS" if candidates else "NO_MATCH"})
    return {"suggestions": suggestions, "exceptions": exceptions, "settled": False}
