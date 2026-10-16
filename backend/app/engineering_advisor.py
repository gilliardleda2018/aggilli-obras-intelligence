"""Deterministic, evidence-first engineering advisory.

This is an advisory rules layer, not an LLM and not an autonomous actor.
No writes, external calls, or synthetic progress. Each finding names its evidence.
"""
from datetime import date
from typing import Any


def assess(project: dict[str, Any], schedule: dict[str, Any], cost: dict[str, Any], *, today: date) -> dict:
    findings = []
    def add(code: str, severity: str, message: str, action: str, evidence: dict):
        findings.append({"code": code, "severity": severity, "message": message,
                         "recommended_action": action, "evidence": evidence})

    if schedule.get("status") == "dados_insuficientes":
        add("SCHEDULE_INPUTS_MISSING", "info", "Não há histórico suficiente para prever o término.",
            "Cadastrar serviços com pesos e registrar medições aprovadas em datas distintas.",
            {"missing": schedule.get("missing", [])})
    elif schedule.get("status") == "sem_produtividade":
        add("PRODUCTIVITY_INSUFFICIENT", "warning", "O histórico não sustenta uma previsão confiável.",
            "Revisar produtividade e registrar novas medições aprovadas.",
            {"missing": schedule.get("missing", [])})
    elif schedule.get("status") == "ok":
        probability = schedule.get("probability_on_time")
        if probability is not None and probability < 0.5:
            add("DEADLINE_RISK", "high", "Probabilidade estimada de entrega no prazo inferior a 50%.",
                "Revisar caminho crítico, recursos e cronograma com o responsável técnico.",
                {"probability_on_time": probability, "finish_p50": schedule.get("finish_p50"),
                 "contract_end": schedule.get("contract_end"), "model": schedule.get("model"),
                 "version": schedule.get("version")})
        for service in schedule.get("critical_services", [])[:3]:
            if service.get("progress", 100) < 100:
                add("CRITICAL_SERVICE", "warning", "Serviço com avanço pendente: " + service["name"],
                    "Verificar medições e impedimentos do serviço.",
                    {"service": service["name"], "progress": service["progress"], "weight": service["weight"]})
    if cost.get("status") == "dados_insuficientes":
        add("COST_INPUTS_MISSING", "info", "Dados insuficientes para estimar custo final.",
            "Revisar orçamento, despesas datadas e medições aprovadas.",
            {"missing": cost.get("missing", [])})
    elif cost.get("status") == "ok" and cost.get("budget") is not None and cost.get("eac_p50") is not None:
        if float(cost["eac_p50"]) > float(cost["budget"]):
            add("COST_OVERRUN_RISK", "high", "Custo final estimado acima do orçamento informado.",
                "Revisar custos comprometidos e planejamento financeiro antes de qualquer decisão.",
                {"budget": cost["budget"], "eac_p50": cost["eac_p50"],
                 "model": cost.get("model"), "version": cost.get("version")})
    if not findings:
        add("NO_ACTIONABLE_RISK", "info", "Nenhum alerta adicional derivável dos dados disponíveis.",
            "Continuar registrando medições e custos reais.", {"schedule_status": schedule.get("status"),
                                                               "cost_status": cost.get("status")})
    priority = {"high": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: (priority[f["severity"]], f["code"], str(f["evidence"])))
    return {"agent": "engenheiro-ia", "version": "1.0", "mode": "advisory",
            "project_id": project["id"], "evaluated_on": today.isoformat(),
            "findings": findings, "writes_performed": False}
