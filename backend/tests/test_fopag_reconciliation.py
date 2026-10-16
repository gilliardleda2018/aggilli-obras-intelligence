from app.fopag_reconciliation import reconcile_contracts


def test_real_source_discrepancies_are_visible_and_never_auto_corrected():
    import json
    from pathlib import Path
    source = json.loads((Path(__file__).resolve().parents[1] / "data" / "tuntum_2026-08-28.json").read_text())
    result = reconcile_contracts(source["contracts"], {
        "contracted": "730169.72", "advances": "195790.00", "reported_balance": "534379.72"})
    assert result["summary"] == {
        "contracted": "736169.72", "advances": "214383.00", "reported_balance": "488086.72"}
    assert not result["ready_for_financial_close"]
    assert not result["money_moved"]
    assert len(result["document_issues"]) == 3
    assert any("BALANCE_MISMATCH" in r["issues"] and r["contractor"] == "Cabiludo" for r in result["rows"])
    assert any("BALANCE_MISMATCH" in r["issues"] and r["contractor"] == "Raimundo BR" for r in result["rows"])


def test_consistent_contracts_can_be_closed_without_stripe():
    result = reconcile_contracts([{"name": "Teste", "project": "A", "total": "100.00",
                                   "advance": "20.00", "balance": "80.00"}],
                                 {"contracted": "100", "advances": "20", "reported_balance": "80"})
    assert result["ready_for_financial_close"] is True
    assert result["provider"] == "MANUAL"
    assert result["money_moved"] is False


def test_missing_total_never_infers_contract_value():
    result = reconcile_contracts([{"name": "Fornecedor", "total": None, "advance": "9", "balance": "9"}])
    assert not result["ready_for_financial_close"]
    assert "CONTRACT_VALUE_MISSING" in result["rows"][0]["issues"]
    assert result["rows"][0]["calculated_balance"] is None
