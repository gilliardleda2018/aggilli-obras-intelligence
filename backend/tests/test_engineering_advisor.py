"""Engineer IA advisory: insufficient evidence, risks, and multi-tenant isolation."""
from datetime import date
from app.engineering_advisor import assess


def test_missing_evidence_never_invents_forecast():
    result = assess({"id": "p1"}, {"status": "dados_insuficientes", "missing": ["medições"]},
                    {"status": "dados_insuficientes", "missing": ["orçamento"]}, today=date(2026, 10, 16))
    assert [x["code"] for x in result["findings"]] == ["COST_INPUTS_MISSING", "SCHEDULE_INPUTS_MISSING"]
    assert result["writes_performed"] is False
    assert all("finish_p50" not in x["evidence"] for x in result["findings"])


def test_high_risk_has_model_evidence():
    result = assess({"id": "p1"}, {"status": "ok", "probability_on_time": 0.2,
                    "finish_p50": "2027-01-01", "contract_end": "2026-12-01",
                    "model": "monte-carlo", "version": "1.0", "critical_services": []},
                    {"status": "ok", "budget": 100, "eac_p50": 150, "model": "evm", "version": "1.0"},
                    today=date(2026, 10, 16))
    assert [x["code"] for x in result["findings"]] == ["COST_OVERRUN_RISK", "DEADLINE_RISK"]
    assert all(x["severity"] == "high" for x in result["findings"])


def test_no_probability_does_not_invent_deadline_risk():
    result = assess({"id": "p1"}, {"status": "ok", "probability_on_time": None, "critical_services": []},
                    {"status": "ok", "budget": None, "eac_p50": None}, today=date(2026, 10, 16))
    assert [x["code"] for x in result["findings"]] == ["NO_ACTIONABLE_RISK"]
