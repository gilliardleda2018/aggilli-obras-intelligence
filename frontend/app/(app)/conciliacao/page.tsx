import {AlertTriangle, BadgeCheck, CalendarClock, Scale, ShieldAlert} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Callout, Card, Kpi} from "../../../components/ui";
import {getDataset, summarize} from "../../../lib/data";
import {compactMoney, money} from "../../../lib/portfolio";

export const dynamic = "force-dynamic";

export default async function Conciliacao() {
  const data = await getDataset();
  const t = summarize(data);
  const flagged = data.schedule.filter(row => row.notes);
  return <>
    {data.error && <div style={{marginBottom: 16}}><Callout icon={AlertTriangle}>{data.error}</Callout></div>}
    <PageHead eyebrow={data.sourceLabel} title="Conciliação"
              subtitle="O que foi devido, o que foi programado e o que já tem comprovante — sem presumir quitação."/>
    <div className="kpis">
      <Kpi label="Obrigações em aberto" value={compactMoney(t.open)} note="sem pagamento comprovado" icon={Scale} tone="warn"/>
      <Kpi label="Programado na semana" value={money(t.weekly)} note={data.weekLabel} icon={CalendarClock}/>
      <Kpi label="Pagamentos comprovados" value={money(t.paid)} note={t.paid ? "com referência de comprovante" : "aguardando comprovantes"}
           icon={BadgeCheck} tone="ok"/>
      <Kpi label="Itens com observação" value={String(flagged.length)} note="conferir antes de pagar" icon={ShieldAlert} tone="info"/>
    </div>
    <div className="grid-2">
      <Card flush title="Lançamentos com observação" subtitle="Resolver antes de pagar">
        {flagged.map(row => <div key={row.key} className="list-item">
          <span className="dot-icon tone-warn"><AlertTriangle/></span>
          <div><b>{row.supplier} · {row.project}</b><small>{row.notes}</small></div>
          <span className="amount">{money(row.amount)}</span>
        </div>)}
        {!flagged.length && <p className="empty">Nenhuma observação pendente.</p>}
      </Card>
      <div className="stack">
        <Callout tone="info" icon={BadgeCheck}>Fluxo do sistema: <b>despesa registrada → pagamento programado → pagamento confirmado
          com comprovante → baixa do saldo</b>, com rateio entre obras aprovado e trilha de auditoria.</Callout>
      </div>
    </div>
  </>;
}
