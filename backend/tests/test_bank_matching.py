from datetime import date
from decimal import Decimal
from app.bank_matching import BankLine, Obligation, suggest_matches


def test_exact_reference_amount_is_suggested_not_settled():
    lines = [BankLine("PIX-ABC", date(2026, 10, 16), Decimal("100.00"))]
    obligations = [Obligation("one", "PIX-ABC", Decimal("100.00"), date(2026, 10, 15))]
    result = suggest_matches(lines, obligations)
    assert result["suggestions"][0]["obligation_id"] == "one"
    assert result["suggestions"][0]["status"] == "SUGGESTED"
    assert result["settled"] is False


def test_different_amount_never_matches():
    result = suggest_matches(
        [BankLine("PIX-ABC", date(2026, 10, 16), Decimal("100.00"))],
        [Obligation("one", "PIX-ABC", Decimal("101.00"), date(2026, 10, 15))])
    assert result["suggestions"] == []
    assert result["exceptions"][0]["reason"] == "NO_MATCH"


def test_ambiguous_reference_is_not_matched():
    line = BankLine("DUP", date(2026, 10, 16), Decimal("50"))
    obligations = [Obligation("one", "DUP", Decimal("50"), date(2026, 10, 16)),
                   Obligation("two", "DUP", Decimal("50"), date(2026, 10, 16))]
    result = suggest_matches([line], obligations)
    assert result["suggestions"] == []
    assert result["exceptions"][0]["reason"] == "AMBIGUOUS"
