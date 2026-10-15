"""Forecasting engine: completion date and final cost, from what was actually recorded.

Methods (established, not invented here):
- Physical progress = weighted sum of approved measurements (service weights).
- Schedule: Monte Carlo over observed productivity (bootstrap of measured intervals), plus Earned Schedule
  (Lipke) when the contract dates give a baseline, plus a deterministic average-rate projection.
- Cost: Earned Value Management (PMI) — EV, CPI, SPI and three EAC formulas — when a budget exists;
  otherwise cost per % of physical progress (run rate) with bootstrap interval.
Every result carries the method, version, inputs used and what is missing. Nothing is produced from
insufficient data: the output says what is needed instead.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

SCHEDULE_MODEL = ("monte-carlo-produtividade", "1.0")
COST_MODEL = ("evm-pmi", "1.0")
RUNRATE_MODEL = ("custo-por-avanco", "1.0")
MIN_POINTS = 3          # distinct measurement dates
MIN_SPAN_DAYS = 14
SIMULATIONS = 5000


@dataclass
class ProjectInputs:
    start_date: date | None
    end_date: date | None
    budget: float | None
    progress: list[tuple[date, float]]            # cumulative physical progress (0-100) at each measurement date
    costs: list[tuple[date, float]]               # cumulative incurred cost at each expense date
    planning_complete: bool
    services: list[dict] = field(default_factory=list)   # name, weight, progress (0-100)
    today: date = field(default_factory=date.today)

    def digest(self) -> str:
        raw = json.dumps({"s": str(self.start_date), "e": str(self.end_date), "b": self.budget,
                          "p": [(str(d), round(v, 4)) for d, v in self.progress],
                          "c": [(str(d), round(v, 2)) for d, v in self.costs], "pc": self.planning_complete,
                          "t": str(self.today)}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()


def _baseline_pct(inputs: ProjectInputs, day: date) -> float | None:
    """Provisional linear baseline between contract start and end (until a detailed baseline exists)."""
    if not inputs.start_date or not inputs.end_date or inputs.end_date <= inputs.start_date:
        return None
    total = (inputs.end_date - inputs.start_date).days
    return float(min(100.0, max(0.0, (day - inputs.start_date).days / total * 100)))


def _series_with_origin(inputs: ProjectInputs) -> list[tuple[date, float]]:
    points = sorted(inputs.progress)
    if inputs.start_date and points and inputs.start_date < points[0][0]:
        points = [(inputs.start_date, 0.0)] + points
    return points


def schedule_forecast(inputs: ProjectInputs) -> dict:
    points = _series_with_origin(inputs)
    measured_dates = sorted({d for d, _ in inputs.progress})
    current = points[-1][1] if points else 0.0
    base = {"model": SCHEDULE_MODEL[0], "version": SCHEDULE_MODEL[1], "contract_end": str(inputs.end_date) if inputs.end_date else None,
            "current_progress": round(current, 2), "inputs": {"measurement_dates": len(measured_dates)}}
    missing = []
    if len(measured_dates) < MIN_POINTS:
        missing.append(f"{MIN_POINTS - len(measured_dates)} data(s) de medição aprovada a mais (mínimo {MIN_POINTS})")
    if points and (points[-1][0] - points[0][0]).days < MIN_SPAN_DAYS:
        missing.append(f"histórico de pelo menos {MIN_SPAN_DAYS} dias entre a primeira e a última medição")
    if not inputs.planning_complete:
        missing.append("pesos dos serviços somando 100% (planejamento completo)")
    if current >= 100:
        return {**base, "status": "concluida", "finish_p50": str(points[-1][0])}
    if missing:
        return {**base, "status": "dados_insuficientes", "missing": missing}

    # Observed productivity per interval (percentage points per day), weighted towards recent intervals.
    rates, spans = [], []
    for (d0, p0), (d1, p1) in zip(points, points[1:]):
        days = (d1 - d0).days
        if days > 0:
            rates.append(max(0.0, (p1 - p0) / days))
            spans.append(days)
    rates_arr, spans_arr = np.array(rates), np.array(spans, dtype=float)
    recency = np.linspace(1.0, 2.0, len(rates_arr))          # recent intervals count up to 2x
    weights = spans_arr * recency
    weights = weights / weights.sum()
    remaining = 100.0 - current
    last_day = points[-1][0]

    average_rate = float(np.average(rates_arr, weights=spans_arr))
    deterministic = None if average_rate <= 0 else last_day + timedelta(days=round(remaining / average_rate))

    rng = np.random.default_rng(int(inputs.digest()[:12], 16))
    block = 7  # productivity is drawn week by week
    # Horizon sized to the slowest plausible pace (25th percentile of positive rates), capped at 10 years.
    positive = rates_arr[rates_arr > 0]
    slow = float(np.percentile(positive, 25)) if len(positive) else 0.0
    horizon_blocks = 520 if slow <= 0 else int(min(520, np.ceil(remaining / (slow * block)) * 3 + 8))
    draws = rng.choice(rates_arr, size=(SIMULATIONS, horizon_blocks), p=weights) * block
    reached = np.cumsum(draws, axis=1) >= remaining
    first = reached.argmax(axis=1)
    finish_days = np.where(reached.any(axis=1), (first + 1) * block, np.inf)
    finite = finish_days[np.isfinite(finish_days)]
    stalled_share = 1 - len(finite) / SIMULATIONS
    if len(finite) < SIMULATIONS * 0.5:
        return {**base, "status": "sem_produtividade", "missing": ["produtividade recente insuficiente para projetar o término"],
                "stalled_share": round(stalled_share, 3)}
    p10, p50, p90 = (last_day + timedelta(days=int(np.percentile(finite, q))) for q in (10, 50, 90))
    result = {**base, "status": "ok", "finish_p10": str(p10), "finish_p50": str(p50), "finish_p90": str(p90),
              "deterministic_finish": str(deterministic) if deterministic else None,
              "productivity": {"average_pp_per_week": round(average_rate * 7, 2),
                               "recent_pp_per_week": round(rates[-1] * 7, 2)},
              "simulations": SIMULATIONS, "stalled_share": round(stalled_share, 3)}
    if inputs.end_date:
        on_time = float(np.mean(finish_days <= (inputs.end_date - last_day).days))
        result["probability_on_time"] = round(on_time, 3)
        result["delay_days_p50"] = (p50 - inputs.end_date).days
        planned_now = _baseline_pct(inputs, last_day)
        if planned_now is not None:
            # Earned Schedule: time at which the baseline reached the current progress.
            total = (inputs.end_date - inputs.start_date).days
            earned_schedule = current / 100 * total
            actual_time = (last_day - inputs.start_date).days
            spi_t = earned_schedule / actual_time if actual_time > 0 else None
            result["earned_schedule"] = {"planned_progress_now": round(planned_now, 2), "spi_t": round(spi_t, 3) if spi_t else None,
                                         "ieac_finish": str(inputs.start_date + timedelta(days=round(total / spi_t))) if spi_t else None,
                                         "baseline": "linear entre início e término contratuais (provisória)"}
    # Retro-test: forecast the last measured point from the previous ones (honest error measure).
    if len(points) >= 5:
        (d_prev, p_prev), (d_last, p_last) = points[-2], points[-1]
        prior = [(d1 - d0).days for (d0, _), (d1, _) in zip(points[:-1], points[1:-1]) if (d1 - d0).days > 0]
        prior_rate = (points[-2][1] - points[0][1]) / max(1, (points[-2][0] - points[0][0]).days)
        result["backtest"] = {"predicted_last_progress": round(p_prev + prior_rate * (d_last - d_prev).days, 2),
                              "actual_last_progress": round(p_last, 2), "intervals_used": len(prior)}
    critical = sorted(inputs.services, key=lambda s: (s["progress"], -s["weight"]))[:3]
    result["critical_services"] = [{"name": s["name"], "progress": s["progress"], "weight": s["weight"]} for s in critical if s["progress"] < 100]
    factors = []
    if rates[-1] < average_rate * 0.8:
        factors.append("produtividade recente abaixo da média — empurra o término para frente")
    elif rates[-1] > average_rate * 1.2:
        factors.append("produtividade recente acima da média — antecipa o término")
    if stalled_share > 0.05:
        factors.append("há períodos sem avanço no histórico, o que alarga o intervalo")
    if result.get("probability_on_time") is not None and result["probability_on_time"] < 0.5:
        factors.append("ritmo atual insuficiente para cumprir a data contratual")
    result["factors"] = factors
    return result


def cost_forecast(inputs: ProjectInputs) -> dict:
    costs = sorted(inputs.costs)
    actual = costs[-1][1] if costs else 0.0
    progress = sorted(inputs.progress)[-1][1] if inputs.progress else 0.0
    base = {"actual_cost": round(actual, 2), "physical_progress": round(progress, 2), "budget": inputs.budget}
    missing = []
    if actual <= 0:
        missing.append("despesas registradas com data")
    if progress < 5:
        missing.append("avanço físico medido de pelo menos 5%")
    if not inputs.planning_complete:
        missing.append("pesos dos serviços somando 100%")
    if missing:
        model = COST_MODEL if inputs.budget else RUNRATE_MODEL
        return {**base, "model": model[0], "version": model[1], "status": "dados_insuficientes", "missing": missing}

    fraction = progress / 100
    if inputs.budget:
        bac = float(inputs.budget)
        ev = bac * fraction
        cpi = ev / actual
        planned_now = _baseline_pct(inputs, costs[-1][0])
        pv = bac * planned_now / 100 if planned_now is not None else None
        spi = ev / pv if pv else None
        estimates = {"bac_sobre_cpi": bac / cpi, "custo_restante_no_orcamento": actual + (bac - ev)}
        if spi:
            estimates["cpi_e_spi"] = actual + (bac - ev) / (cpi * spi)
        values = list(estimates.values())
        p50 = estimates["bac_sobre_cpi"]
        return {**base, "model": COST_MODEL[0], "version": COST_MODEL[1], "status": "ok",
                "earned_value": round(ev, 2), "planned_value": round(pv, 2) if pv else None, "cpi": round(cpi, 3),
                "spi": round(spi, 3) if spi else None, "eac_p50": round(p50, 2), "eac_low": round(min(values), 2),
                "eac_high": round(max(values), 2), "vac": round(bac - p50, 2),
                "methods": {k: round(v, 2) for k, v in estimates.items()},
                "factors": (["custo por avanço acima do orçado (CPI < 1)"] if cpi < 1 else ["custo por avanço dentro do orçado (CPI ≥ 1)"])}

    # No budget: cost per percentage point of progress, with bootstrap over measured intervals.
    per_point = actual / progress
    p50 = per_point * 100
    increments = []
    prog = sorted(inputs.progress)
    for (d0, p0), (d1, p1) in zip(prog, prog[1:]):
        spent = _cost_at(costs, d1) - _cost_at(costs, d0)
        if p1 > p0 and spent >= 0:
            increments.append(spent / (p1 - p0))
    low = high = p50
    if len(increments) >= 2:
        rng = np.random.default_rng(int(inputs.digest()[:12], 16))
        remaining_points = 100 - progress
        sims = actual + rng.choice(np.array(increments), size=(SIMULATIONS, max(1, int(remaining_points)))).mean(axis=1) * remaining_points
        low, p50, high = (float(np.percentile(sims, q)) for q in (10, 50, 90))
    return {**base, "model": RUNRATE_MODEL[0], "version": RUNRATE_MODEL[1], "status": "ok", "cost_per_point": round(per_point, 2),
            "eac_p50": round(p50, 2), "eac_low": round(low, 2), "eac_high": round(high, 2),
            "factors": ["sem orçamento contratual: estimativa pelo custo por ponto de avanço medido"]}


def _cost_at(costs: list[tuple[date, float]], day: date) -> float:
    value = 0.0
    for d, cumulative in costs:
        if d <= day:
            value = cumulative
    return value
