import type {CostForecast, ProjectIntelligence, ScheduleForecast} from "../lib/api";
import {money} from "../lib/portfolio";
import {TimeChart, type Point} from "./time-chart";

export const br = (iso?: string | null) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "—");
const MODEL_LABEL: Record<string, string> = {
  "monte-carlo-produtividade": "Monte Carlo de produtividade", "evm-pmi": "Valor agregado (EVM/PMI)", "custo-por-avanco": "Custo por ponto de avanço",
};
export const modelLabel = (model: string, version: string) => (MODEL_LABEL[model] ?? model) + " · v" + version;

export function Probability({value}: {value?: number}) {
  if (value === undefined || value === null) return <span className="prob tone-neutral">—</span>;
  const pct = Math.round(value * 100);
  const tone = pct >= 70 ? "tone-ok" : pct >= 40 ? "tone-warn" : "tone-danger";
  return <span className={"prob " + tone} title="Probabilidade de concluir até a data contratual (simulação; ainda não calibrada)">{pct}%</span>;
}

export function Missing({items}: {items?: string[] | null}) {
  if (!items?.length) return null;
  return <ul className="missing">{items.map(item => <li key={item}>falta: {item}</li>)}</ul>;
}

export function ScheduleSummary({s}: {s: ScheduleForecast}) {
  if (s.status === "concluida") return <div><div className="forecast-big">Concluída</div><div className="forecast-range">em {br(s.finish_p50)}</div></div>;
  if (s.status !== "ok") return <div><div className="forecast-range"><b>Sem previsão ainda</b> · avanço medido {s.current_progress.toLocaleString("pt-BR")}%</div>
    <Missing items={s.missing}/></div>;
  return <div>
    <div className="forecast-big">{br(s.finish_p50)}</div>
    <div className="forecast-range">entre {br(s.finish_p10)} e {br(s.finish_p90)}
      {s.delay_days_p50 !== undefined && (s.delay_days_p50 > 0 ? ` · ${s.delay_days_p50} dias após o contrato` : " · dentro do prazo")}</div>
  </div>;
}

export function CostSummary({c}: {c: CostForecast}) {
  if (c.status !== "ok") return <div><div className="forecast-range"><b>Sem previsão ainda</b> · gasto {money(c.actual_cost)}</div><Missing items={c.missing}/></div>;
  return <div>
    <div className="forecast-big">{money(c.eac_p50!)}</div>
    <div className="forecast-range">entre {money(c.eac_low!)} e {money(c.eac_high!)}
      {c.budget ? ` · orçamento ${money(c.budget)}` : " · sem orçamento informado"}{c.cpi ? ` · CPI ${c.cpi.toLocaleString("pt-BR")}` : ""}</div>
  </div>;
}

/** S-curve: measured progress, contract baseline and forecast band to completion. */
export function ProgressChart({data}: {data: ProjectIntelligence}) {
  const actual: Point[] = data.series.progress.map(p => ({x: p.date, y: p.progress}));
  const s = data.schedule;
  const last = actual[actual.length - 1];
  const band = s.status === "ok" && last ? {
    name: "Faixa de previsão (P10–P90)", color: "#3b6fb6",
    lower: [last, {x: s.finish_p90!, y: 100}], upper: [last, {x: s.finish_p10!, y: 100}],
  } : undefined;
  return <TimeChart ariaLabel="Curva S do avanço físico" yMax={100} yFormat="percent" band={band}
    series={[
      {name: "Avanço medido", color: "#2f9a7e", points: actual},
      {name: "Linha de base contratual", color: "#8a94a6", points: data.series.baseline.map(p => ({x: p.date, y: p.progress})), dashed: true},
      ...(s.status === "ok" && last ? [{name: "Previsão central (P50)", color: "#3b6fb6", points: [last, {x: s.finish_p50!, y: 100}], dashed: true}] : []),
    ]}
    markers={[...(s.contract_end ? [{x: s.contract_end, label: "Término contratual", color: "#b07a30"}] : [])]}/>;
}

/** Cumulative cost with projection to the estimated final cost. */
export function CostChart({data}: {data: ProjectIntelligence}) {
  const actual: Point[] = data.series.cost.map(p => ({x: p.date, y: p.cost}));
  const c = data.cost, s = data.schedule;
  const last = actual[actual.length - 1];
  const end = s.status === "ok" ? s.finish_p50! : s.contract_end;
  const projected = c.status === "ok" && last && end ? [{name: "Custo final estimado", color: "#a4583c", points: [last, {x: end, y: c.eac_p50!}], dashed: true}] : [];
  const budget = c.budget && actual.length ? [{name: "Orçamento", color: "#8a94a6", dashed: true,
    points: [{x: actual[0].x, y: c.budget}, {x: end ?? last.x, y: c.budget}]}] : [];
  const band = c.status === "ok" && last && end ? {name: "Faixa do custo final", color: "#a4583c",
    lower: [last, {x: end, y: c.eac_low!}], upper: [last, {x: end, y: c.eac_high!}]} : undefined;
  return <TimeChart ariaLabel="Custo acumulado e projeção" band={band} yFormat="money"
    series={[{name: "Custo incorrido acumulado", color: "#3b6fb6", points: actual}, ...budget, ...projected]}/>;
}
