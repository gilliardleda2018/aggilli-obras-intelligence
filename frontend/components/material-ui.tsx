import {Badge} from "./ui";

export const FLAG = {
  estoque_baixo: {label: "Estoque baixo", tone: "warn"}, ruptura_proxima: {label: "Ruptura próxima", tone: "danger"},
  consumo_acima: {label: "Consumo acima do avanço", tone: "danger"},
} as const;
export const qty = (value: string | null) => (value === null ? "—" : Number(value).toLocaleString("pt-BR", {maximumFractionDigits: 3}));
export const brl = (value: string | null) =>
  value === null ? "—" : Number(value).toLocaleString("pt-BR", {style: "currency", currency: "BRL", minimumFractionDigits: 2});

export function Flags({flags}: {flags: string[]}) {
  if (!flags.length) return <Badge tone="ok">Normal</Badge>;
  return <span style={{display: "inline-flex", gap: 4, flexWrap: "wrap"}}>
    {flags.map(f => <Badge key={f} tone={FLAG[f as keyof typeof FLAG]?.tone ?? "neutral"}>{FLAG[f as keyof typeof FLAG]?.label ?? f}</Badge>)}</span>;
}

export function Coverage({days}: {days: number | null}) {
  if (days === null) return <span className="cell-sub" style={{display: "inline"}}>sem consumo em 30 dias</span>;
  return <b style={{color: days <= 7 ? "var(--danger)" : days <= 15 ? "var(--warn)" : undefined}}>{days} dias</b>;
}
