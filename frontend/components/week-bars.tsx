import type {TrendWeek} from "../lib/api";

/** Weekly grouped bars: cost incurred × paid with evidence × scheduled. */
export function WeekBars({weeks}: {weeks: TrendWeek[]}) {
  const W = 720, H = 220, L = 56, B = 30, T = 12;
  const series = [
    {key: "incurred_total" as const, name: "Custo incorrido", color: "#3367d6"},
    {key: "paid" as const, name: "Pago (comprovado)", color: "#0f9d58"},
    {key: "scheduled" as const, name: "Programado", color: "#b7791f"},
  ];
  const max = Math.max(1, ...weeks.flatMap(w => series.map(s => Number(w[s.key])))) * 1.1;
  const slot = (W - L - 8) / weeks.length;
  const bar = Math.min(14, (slot - 6) / 3);
  const y = (v: number) => T + (1 - v / max) * (H - T - B);
  const fmt = (v: number) => v >= 1000 ? (v / 1000).toLocaleString("pt-BR", {maximumFractionDigits: 0}) + " mil" : v.toFixed(0);
  return <figure className="chart" aria-label="Evolução semanal de custos e pagamentos">
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Evolução semanal de custos e pagamentos">
      {[0, 0.5, 1].map(f => <g key={f}><line x1={L} x2={W - 8} y1={y(f * max)} y2={y(f * max)} className="grid"/>
        <text x={L - 8} y={y(f * max) + 4} textAnchor="end" className="tick">R$ {fmt(f * max)}</text></g>)}
      {weeks.map((w, i) => <g key={w.week_start}>
        {series.map((s, j) => {
          const value = Number(w[s.key]);
          return value > 0 && <rect key={s.key} x={L + i * slot + (slot - 3 * bar) / 2 + j * bar} y={y(value)} width={bar - 2}
            height={H - B - y(value)} rx={2} fill={s.color}><title>{s.name}: R$ {value.toLocaleString("pt-BR", {minimumFractionDigits: 2})}</title></rect>;
        })}
        {(weeks.length <= 12 || i % 2 === 0) && <text x={L + i * slot + slot / 2} y={H - 10} textAnchor="middle" className="tick">
          {w.week_start.slice(8, 10)}/{w.week_start.slice(5, 7)}</text>}
      </g>)}
    </svg>
    <figcaption>{series.map(s => <span key={s.key}><i style={{background: s.color}}/>{s.name}</span>)}</figcaption>
  </figure>;
}
