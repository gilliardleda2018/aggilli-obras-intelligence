"use client";
/** SVG time chart: lines (solid/dashed) with a soft area wash under the main series, an optional uncertainty band,
 * vertical markers and a crosshair tooltip that snaps to the nearest date and lists every series there. */
import {useId, useState, type PointerEvent} from "react";

export type Point = {x: string; y: number};
export type Series = {name: string; color: string; points: Point[]; dashed?: boolean};
export type Marker = {x: string; label: string; color: string};
export type YFormat = "number" | "percent" | "money";

const W = 720, H = 260, R = 18, T = 18, B = 34;
const t = (iso: string) => new Date(iso.slice(0, 10) + "T12:00:00").getTime();
const brDate = (ms: number) => new Date(ms).toLocaleDateString("pt-BR", {day: "2-digit", month: "2-digit", year: "2-digit"});

function formatter(kind: YFormat, compact: boolean) {
  if (kind === "percent") return (v: number) => v.toLocaleString("pt-BR", {maximumFractionDigits: compact ? 0 : 1}) + "%";
  if (kind === "money") return (v: number) => compact && Math.abs(v) >= 1000
    ? "R$ " + (v / 1000).toLocaleString("pt-BR", {maximumFractionDigits: 0}) + " mil"
    : v.toLocaleString("pt-BR", {style: "currency", currency: "BRL", maximumFractionDigits: compact ? 0 : 2});
  return (v: number) => v.toLocaleString("pt-BR", {maximumFractionDigits: compact ? 0 : 2});
}

export function TimeChart({series, band, markers = [], yFormat = "number", yMax, ariaLabel}:
  {series: Series[]; band?: {lower: Point[]; upper: Point[]; color: string; name: string}; markers?: Marker[];
   yFormat?: YFormat; yMax?: number; ariaLabel: string}) {
  const id = useId().replace(/:/g, "");
  const [hover, setHover] = useState<number | null>(null);
  const all = [...series.flatMap(s => s.points), ...(band ? [...band.lower, ...band.upper] : []), ...markers.map(m => ({x: m.x, y: 0}))];
  if (!all.length) return <p className="empty">Sem dados para o gráfico.</p>;
  const tick = formatter(yFormat, true), full = formatter(yFormat, false);
  const L = yFormat === "money" ? 78 : 52;  // room for the widest y tick
  const xs = all.map(p => t(p.x));
  const x0 = Math.min(...xs), x1 = Math.max(...xs) === x0 ? x0 + 86400000 : Math.max(...xs);
  const top = yMax ?? Math.max(1, ...all.map(p => p.y)) * 1.08;
  const px = (ms: number) => L + ((ms - x0) / (x1 - x0)) * (W - L - R);
  const sx = (iso: string) => px(t(iso));
  const sy = (v: number) => T + (1 - v / top) * (H - T - B);
  const path = (points: Point[]) => points.map((p, i) => (i ? "L" : "M") + sx(p.x).toFixed(1) + " " + sy(p.y).toFixed(1)).join(" ");
  const ticksY = [0, 0.25, 0.5, 0.75, 1].map(f => f * top);
  const ticksX = [0, 0.25, 0.5, 0.75, 1].map(f => x0 + f * (x1 - x0));
  const main = series.find(s => !s.dashed && s.points.length > 0);
  const last = main?.points[main.points.length - 1];
  // Crosshair snaps to the dates that actually have values.
  const dates = [...new Set(series.flatMap(s => s.points.map(p => t(p.x))))].sort((a, b) => a - b);
  const rows = hover === null ? [] : series.flatMap(s => {
    const point = s.points.find(p => t(p.x) === hover);
    return point ? [{name: s.name, color: s.color, dashed: s.dashed, value: point.y}] : [];
  });

  function move(event: PointerEvent<SVGRectElement>) {
    const rect = (event.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * W;
    const ms = x0 + ((x - L) / (W - L - R)) * (x1 - x0);
    setHover(dates.reduce((best, d) => (Math.abs(d - ms) < Math.abs(best - ms) ? d : best), dates[0]));
  }

  const hx = hover === null ? 0 : px(hover);
  return <figure className="chart" aria-label={ariaLabel}>
    <div className="chart-plot">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel}>
        <defs>
          {main && <linearGradient id={id + "-area"} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={main.color} stopOpacity=".22"/><stop offset="100%" stopColor={main.color} stopOpacity="0"/>
          </linearGradient>}
          {band && <linearGradient id={id + "-band"} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={band.color} stopOpacity=".26"/><stop offset="100%" stopColor={band.color} stopOpacity=".08"/>
          </linearGradient>}
        </defs>
        {ticksY.map(v => <g key={v}><line x1={L} x2={W - R} y1={sy(v)} y2={sy(v)} className={v === 0 ? "baseline" : "grid"}/>
          <text x={L - 10} y={sy(v) + 4} textAnchor="end" className="tick">{tick(v)}</text></g>)}
        {ticksX.map((v, i) => <text key={v} x={px(v)} y={H - 10} textAnchor={i === 0 ? "start" : i === ticksX.length - 1 ? "end" : "middle"}
                                     className="tick">{brDate(v)}</text>)}
        {band && band.lower.length > 1 && <path fill={`url(#${id}-band)`}
          d={path(band.upper) + " " + [...band.lower].reverse().map(p => "L" + sx(p.x).toFixed(1) + " " + sy(p.y).toFixed(1)).join(" ") + " Z"}/>}
        {main && main.points.length > 1 && <path className="chart-area" fill={`url(#${id}-area)`}
          d={path(main.points) + ` L${sx(main.points[main.points.length - 1].x).toFixed(1)} ${sy(0)} L${sx(main.points[0].x).toFixed(1)} ${sy(0)} Z`}/>}
        {markers.map(m => <g key={m.label}><line x1={sx(m.x)} x2={sx(m.x)} y1={T} y2={H - B} stroke={m.color} strokeWidth={1.5} strokeDasharray="2 4"
                                                  strokeLinecap="round"/>
          <text x={sx(m.x) - 6} y={T + 10} textAnchor="end" className="tick marker-label">{m.label}</text></g>)}
        {series.map(s => s.points.length > 0 && <path key={s.name} className={s.dashed ? "chart-line dashed" : "chart-line"} d={path(s.points)} fill="none"
          stroke={s.color} strokeWidth={s.dashed ? 1.75 : 2.25} strokeDasharray={s.dashed ? "5 5" : undefined} strokeLinejoin="round" strokeLinecap="round"/>)}
        {last && <g className="end-dot"><circle cx={sx(last.x)} cy={sy(last.y)} r={9} fill={main!.color} opacity=".16"/>
          <circle cx={sx(last.x)} cy={sy(last.y)} r={5} fill={main!.color} stroke="var(--surface)" strokeWidth={2}/></g>}
        {hover !== null && <g className="crosshair" pointerEvents="none">
          <line x1={hx} x2={hx} y1={T} y2={H - B}/>
          {rows.map(r => <circle key={r.name} cx={hx} cy={sy(r.value)} r={4.5} fill={r.color} stroke="var(--surface)" strokeWidth={2}/>)}
        </g>}
        <rect x={L} y={T} width={W - L - R} height={H - T - B} fill="transparent" onPointerMove={move} onPointerLeave={() => setHover(null)}/>
      </svg>
      {hover !== null && rows.length > 0 && <div className="chart-tip" style={{left: (hx / W) * 100 + "%"}} data-side={hx > W * .62 ? "left" : "right"}>
        <b className="chart-tip-date">{brDate(hover)}</b>
        {rows.map(r => <span key={r.name}><i style={{background: r.color, opacity: r.dashed ? .7 : 1}}/><strong>{full(r.value)}</strong>{r.name}</span>)}
      </div>}
    </div>
    <figcaption>
      {series.map(s => <span key={s.name}><i className={s.dashed ? "dashed" : ""} style={{background: s.color}}/>{s.name}</span>)}
      {band && <span><i className="swatch" style={{background: band.color, opacity: .35}}/>{band.name}</span>}
      {markers.map(m => <span key={m.label}><i className="dashed" style={{background: m.color}}/>{m.label}</span>)}
    </figcaption>
  </figure>;
}
