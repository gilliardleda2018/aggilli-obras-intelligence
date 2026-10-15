/** Lightweight SVG time chart: lines (solid/dashed), an optional uncertainty band and vertical markers. */
export type Point = {x: string; y: number};
export type Series = {name: string; color: string; points: Point[]; dashed?: boolean};
export type Marker = {x: string; label: string; color: string};

const W = 720, H = 260, L = 56, R = 16, T = 16, B = 34;
const t = (iso: string) => new Date(iso + "T12:00:00").getTime();
const brDate = (ms: number) => new Date(ms).toLocaleDateString("pt-BR", {day: "2-digit", month: "2-digit", year: "2-digit"});

export function TimeChart({series, band, markers = [], yFormat = (v: number) => v.toLocaleString("pt-BR"), yMax, ariaLabel}:
  {series: Series[]; band?: {lower: Point[]; upper: Point[]; color: string; name: string}; markers?: Marker[];
   yFormat?: (v: number) => string; yMax?: number; ariaLabel: string}) {
  const all = [...series.flatMap(s => s.points), ...(band ? [...band.lower, ...band.upper] : []), ...markers.map(m => ({x: m.x, y: 0}))];
  if (!all.length) return <p className="empty">Sem dados para o gráfico.</p>;
  const xs = all.map(p => t(p.x));
  const x0 = Math.min(...xs), x1 = Math.max(...xs) === x0 ? x0 + 86400000 : Math.max(...xs);
  const top = yMax ?? Math.max(1, ...all.map(p => p.y)) * 1.08;
  const sx = (iso: string) => L + ((t(iso) - x0) / (x1 - x0)) * (W - L - R);
  const sy = (v: number) => T + (1 - v / top) * (H - T - B);
  const path = (points: Point[]) => points.map((p, i) => (i ? "L" : "M") + sx(p.x).toFixed(1) + " " + sy(p.y).toFixed(1)).join(" ");
  const ticksY = [0, 0.25, 0.5, 0.75, 1].map(f => f * top);
  const ticksX = [0, 0.25, 0.5, 0.75, 1].map(f => x0 + f * (x1 - x0));
  return <figure className="chart" aria-label={ariaLabel}>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel}>
      {ticksY.map(v => <g key={v}><line x1={L} x2={W - R} y1={sy(v)} y2={sy(v)} className="grid"/>
        <text x={L - 8} y={sy(v) + 4} textAnchor="end" className="tick">{yFormat(v)}</text></g>)}
      {ticksX.map(v => <text key={v} x={L + ((v - x0) / (x1 - x0)) * (W - L - R)} y={H - 10} textAnchor="middle" className="tick">{brDate(v)}</text>)}
      {band && band.lower.length > 1 && <path className="band" style={{fill: band.color}}
        d={path(band.upper) + " " + [...band.lower].reverse().map(p => "L" + sx(p.x).toFixed(1) + " " + sy(p.y).toFixed(1)).join(" ") + " Z"}/>}
      {series.map(s => s.points.length > 0 && <g key={s.name}>
        <path d={path(s.points)} fill="none" stroke={s.color} strokeWidth={2.4} strokeDasharray={s.dashed ? "6 5" : undefined}
              strokeLinejoin="round" strokeLinecap="round"/>
        {!s.dashed && s.points.length < 40 && s.points.map(p => <circle key={p.x} cx={sx(p.x)} cy={sy(p.y)} r={2.6} fill={s.color}/>)}
      </g>)}
      {markers.map(m => <g key={m.label}><line x1={sx(m.x)} x2={sx(m.x)} y1={T} y2={H - B} stroke={m.color} strokeDasharray="3 4"/>
        <text x={sx(m.x) + 4} y={T + 10} className="tick" style={{fill: m.color}}>{m.label}</text></g>)}
    </svg>
    <figcaption>
      {series.map(s => <span key={s.name}><i style={{background: s.color, opacity: s.dashed ? .6 : 1}}/>{s.name}</span>)}
      {band && <span><i style={{background: band.color}}/>{band.name}</span>}
    </figcaption>
  </figure>;
}
