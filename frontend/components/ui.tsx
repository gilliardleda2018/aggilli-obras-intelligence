import type {CSSProperties, ReactNode} from "react";
import type {LucideIcon} from "lucide-react";

export type Tone = "brand" | "ok" | "warn" | "danger" | "info";

export function Kpi({label, value, note, icon: Icon, tone = "brand"}:
  {label: string; value: string; note: string; icon: LucideIcon; tone?: Tone}) {
  return <article className={"card kpi kpi-" + tone}>
    <div className="kpi-top">{label}<span className={"kpi-icon tone-" + tone}><Icon/></span></div>
    <div className="kpi-value">{value}</div>
    <div className="kpi-note">{note}</div>
  </article>;
}

export function Card({title, subtitle, action, children, flush}:
  {title?: string; subtitle?: string; action?: ReactNode; children: ReactNode; flush?: boolean}) {
  return <section className="card">
    {title && <div className="card-head"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>}
    {flush ? children : <div className="card-body">{children}</div>}
  </section>;
}

const METER_TONE: Record<string, string> = {"var(--ok)": "var(--sage)", "var(--warn)": "var(--ochre)", "var(--danger)": "var(--terra)"};

export function Meter({value, tone}: {value: number; tone?: string}) {
  const width = Math.max(0, Math.min(100, value));
  const color = tone ? METER_TONE[tone] ?? tone : "var(--brand)";
  return <div className="meter" role="meter" aria-valuenow={width} aria-valuemin={0} aria-valuemax={100}
              style={{"--m": color} as CSSProperties}>
    <span style={{width: width + "%"}}/>
  </div>;
}

export function Badge({tone, children}: {tone?: Tone | "neutral"; children: ReactNode}) {
  return <span className={"badge " + (tone === "neutral" || !tone ? "neutral" : "tone-" + tone)}><i/>{children}</span>;
}

export function Callout({tone = "warn", icon: Icon, children}: {tone?: "warn" | "info"; icon: LucideIcon; children: ReactNode}) {
  return <div className={"callout" + (tone === "info" ? " info" : "")}><Icon/><div>{children}</div></div>;
}
