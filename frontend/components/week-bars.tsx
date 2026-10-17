"use client";
import {useId, useState} from "react";
import type {TrendWeek} from "../lib/api";

// Validated categorical order (dataviz validator: CVD ΔE ≥ 8, contrast ≥ 3:1 on the card surface).
const SERIES = [
  {key: "incurred_total" as const, name: "Custo incorrido", color: "#3b6fb6"},
  {key: "paid" as const, name: "Pago (comprovado)", color: "#2f9a7e"},
  {key: "scheduled" as const, name: "Programado", color: "#b07a30"},
];
const brl = (v: number) => v.toLocaleString("pt-BR", {style: "currency", currency: "BRL"});
const compact = (v: number) => v >= 1000 ? (v / 1000).toLocaleString("pt-BR", {maximumFractionDigits: 0}) + " mil" : v.toFixed(0);

/** Column with a 4px rounded top and a square base on the baseline. */
function column(x: number, y: number, w: number, base: number) {
  const r = Math.min(4, w / 2, base - y);
  return `M${x} ${base}V${y + r}Q${x} ${y} ${x + r} ${y}H${x + w - r}Q${x + w} ${y} ${x + w} ${y + r}V${base}Z`;
}

/** Weekly grouped bars: cost incurred × paid with evidence × scheduled, with a per-week hover readout. */
export function WeekBars({weeks}: {weeks: TrendWeek[]}) {
  const id = useId().replace(/:/g, "");
  const [hover, setHover] = useState<number | null>(null);
  const W = 720, H = 230, L = 60, R = 8, B = 30, T = 14;
  const max = Math.max(1, ...weeks.flatMap(w => SERIES.map(s => Number(w[s.key])))) * 1.1;
  const slot = (W - L - R) / Math.max(1, weeks.length);
  const bar = Math.min(16, (slot - 10) / 3);
  const base = H - B;
  const y = (v: number) => T + (1 - v / max) * (H - T - B);
  const week = hover === null ? null : weeks[hover];
  return <figure className="chart" aria-label="Evolução semanal de custos e pagamentos">
    <div className="chart-plot">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Evolução semanal de custos e pagamentos" onPointerLeave={() => setHover(null)}>
        <defs>{SERIES.map(s => <linearGradient key={s.key} id={`${id}-${s.key}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={s.color}/><stop offset="100%" stopColor={s.color} stopOpacity=".72"/>
        </linearGradient>)}</defs>
        {[0, 0.25, 0.5, 0.75, 1].map(f => <g key={f}><line x1={L} x2={W - R} y1={y(f * max)} y2={y(f * max)} className={f === 0 ? "baseline" : "grid"}/>
          <text x={L - 10} y={y(f * max) + 4} textAnchor="end" className="tick">R$ {compact(f * max)}</text></g>)}
        {weeks.map((w, i) => {
          const x = L + i * slot;
          return <g key={w.week_start} className={"week" + (hover === null ? "" : hover === i ? " on" : " off")}>
            {hover === i && <rect x={x + 2} y={T - 6} width={slot - 4} height={base - T + 6} rx={8} className="week-band"/>}
            {SERIES.map((s, j) => {
              const value = Number(w[s.key]);
              if (!(value > 0)) return null;
              const bx = x + (slot - 3 * bar) / 2 + j * bar;
              return <path key={s.key} className="bar" style={{animationDelay: i * 25 + "ms"}} d={column(bx, y(value), bar - 2, base)}
                           fill={`url(#${id}-${s.key})`}/>;
            })}
            {(weeks.length <= 12 || i % 2 === 0) && <text x={x + slot / 2} y={H - 10} textAnchor="middle" className="tick">
              {w.week_start.slice(8, 10)}/{w.week_start.slice(5, 7)}</text>}
            <rect x={x} y={T} width={slot} height={base - T} fill="transparent" tabIndex={0} aria-label={"Semana de " + w.week_start}
                  onPointerEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)}/>
          </g>;
        })}
      </svg>
      {week && <div className="chart-tip" style={{left: ((L + (hover! + .5) * slot) / W) * 100 + "%"}} data-side={hover! > weeks.length * .6 ? "left" : "right"}>
        <b className="chart-tip-date">Semana de {week.week_start.slice(8, 10)}/{week.week_start.slice(5, 7)}</b>
        {SERIES.map(s => <span key={s.key}><i style={{background: s.color}}/><strong>{brl(Number(week[s.key]))}</strong>{s.name}</span>)}
      </div>}
    </div>
    <figcaption>{SERIES.map(s => <span key={s.key}><i className="swatch" style={{background: s.color}}/>{s.name}</span>)}</figcaption>
  </figure>;
}
