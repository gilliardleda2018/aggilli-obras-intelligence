"use client";
import {useActionState} from "react";
import Link from "next/link";
import {AlertOctagon, AlertTriangle, Check, Info, ThumbsDown, X} from "lucide-react";
import {reviewAlert, type ReviewState} from "../lib/alert-actions";
import type {Alert} from "../lib/api";
import {Badge} from "./ui";

const TYPE: Record<string, string> = {
  possivel_duplicidade: "Possível duplicidade", valor_incomum: "Valor incomum", pagamento_vencido: "Pagamento sem confirmação",
  medicao_parada: "Medição parada", risco_atraso: "Risco de atraso", risco_estouro: "Risco de estouro", queda_produtividade: "Queda de produtividade",
  sem_medicao_recente: "Sem medição recente",
};
const ICON = {high: AlertOctagon, medium: AlertTriangle, low: Info};
const TONE = {high: "tone-danger", medium: "tone-warn", low: "tone-info"} as const;
const DECISION: Record<string, string> = {CONFIRMED: "Procedente", FALSE_ALARM: "Falso alarme", RESOLVED: "Resolvido"};

function ReviewButtons({alertKey}: {alertKey: string}) {
  const [state, action, pending] = useActionState(reviewAlert.bind(null, alertKey), {ok: false, message: ""} as ReviewState);
  if (state.ok) return <span className="feedback ok">{state.message}</span>;
  return <form action={action} style={{display: "grid", gap: 6, justifyItems: "end"}}>
    <input className="input" name="note" placeholder="Observação (opcional)" maxLength={500} style={{height: 32, width: 220}}/>
    <div style={{display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end"}}>
      <button className="btn" name="decision" value="CONFIRMED" disabled={pending} title="O alerta faz sentido"><Check/>Procedente</button>
      <button className="btn" name="decision" value="RESOLVED" disabled={pending} title="Já foi tratado"><X/>Resolvido</button>
      <button className="btn" name="decision" value="FALSE_ALARM" disabled={pending} title="Ensina o sistema a evitar este tipo de aviso">
        <ThumbsDown/>Falso alarme</button>
    </div>
    {state.message && <span className="feedback err">{state.message}</span>}
  </form>;
}

export function AlertList({alerts, compact = false}: {alerts: Alert[]; compact?: boolean}) {
  if (!alerts.length) return <p className="empty">Nenhum alerta em aberto. O sistema continua verificando a cada lançamento.</p>;
  return <>{alerts.map(alert => {
    const Icon = ICON[alert.severity];
    return <div key={alert.key} className="list-item" style={{alignItems: "flex-start"}}>
      <span className={"dot-icon " + TONE[alert.severity]}><Icon/></span>
      <div style={{flex: 1, minWidth: 0}}>
        <b>{alert.title}</b>
        <small><Link className="link" style={{fontWeight: 500}} href={"/obras/" + alert.project_id}>{alert.project}</Link> · {TYPE[alert.type] ?? alert.type}</small>
        <small>{alert.detail}</small>
        {!compact && alert.evidence.length > 0 && <small className="cell-sub">Registros: {alert.evidence.map(e => e.label).join(" · ")}</small>}
        {alert.review && <Badge tone="neutral">{DECISION[alert.review.decision]} por {alert.review.by}{alert.review.note ? " — " + alert.review.note : ""}</Badge>}
      </div>
      {!compact && !alert.review && <ReviewButtons alertKey={alert.key}/>}
    </div>;
  })}</>;
}
