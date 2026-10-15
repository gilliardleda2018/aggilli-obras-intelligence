import {AlertOctagon, AlertTriangle, BellRing, Info, Lock, LogIn} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {AlertList} from "../../../components/alert-list";
import {Callout, Card, Kpi} from "../../../components/ui";
import {apiGet, type AlertsResponse} from "../../../lib/api";

export const dynamic = "force-dynamic";
const TYPE: Record<string, string> = {
  possivel_duplicidade: "Possível duplicidade", valor_incomum: "Valor incomum", pagamento_vencido: "Pagamento sem confirmação",
  medicao_parada: "Medição parada", risco_atraso: "Risco de atraso", risco_estouro: "Risco de estouro", queda_produtividade: "Queda de produtividade",
  sem_medicao_recente: "Sem medição recente",
};

export default async function Alertas({searchParams}: {searchParams: Promise<{todos?: string}>}) {
  const {todos} = await searchParams;
  const data = await apiGet<AlertsResponse>("/alerts" + (todos ? "?include_reviewed=true" : ""));
  if (!data) return <>
    <PageHead title="Alertas" subtitle="Sinais automáticos sobre custos, pagamentos, medições e previsões."/>
    <Callout tone="info" icon={Lock}>Entre para ver os alertas. <a className="link" href="/login"><LogIn size={14}/> Entrar</a></Callout>
  </>;
  const open = data.alerts.filter(a => !a.review);
  const count = (severity: string) => open.filter(a => a.severity === severity).length;
  const feedback = Object.entries(data.feedback);
  return <>
    <PageHead eyebrow="Inteligência" title="Alertas"
              subtitle="O sistema verifica tudo o que é lançado: duplicidades, valores fora do padrão, pagamentos sem comprovante, medições paradas e riscos de prazo e custo."
              actions={<a className="btn" href={todos ? "/alertas" : "/alertas?todos=1"}>{todos ? "Só em aberto" : "Ver também os revisados"}</a>}/>
    <div className="kpis">
      <Kpi label="Em aberto" value={String(data.open)} note="aguardando revisão" icon={BellRing}/>
      <Kpi label="Alta prioridade" value={String(count("high"))} note="duplicidade, atraso ou estouro" icon={AlertOctagon} tone="danger"/>
      <Kpi label="Média" value={String(count("medium"))} note="pagamentos e produtividade" icon={AlertTriangle} tone="warn"/>
      <Kpi label="Baixa" value={String(count("low"))} note="valores e dados desatualizados" icon={Info} tone="info"/>
    </div>
    <div className="grid-main">
      <Card flush title="Alertas" subtitle="Ordenados por prioridade; cada um mostra o motivo e os registros de origem">
        <AlertList alerts={data.alerts}/>
      </Card>
      <div className="stack">
        <Card title="Aprendizado com as revisões" subtitle="Procedentes × falsos alarmes por tipo">
          {feedback.length ? <div className="bars">{feedback.map(([type, f]) => <div key={type} className="bar-row" style={{gridTemplateColumns: "1fr auto"}}>
            <span>{TYPE[type] ?? type}</span><b>{f.confirmed} procedentes · {f.false_alarm} falsos</b></div>)}</div>
            : <p className="empty">Ainda sem revisões. Marque os alertas como procedentes ou falso alarme para calibrar a detecção.</p>}
        </Card>
        <Callout tone="info" icon={Info}>Um alerta é um sinal para conferir, nunca uma acusação. Regras de negócio são a primeira barreira e
          estatística robusta (mediana e desvio absoluto) apoia a detecção de valores fora do padrão.</Callout>
      </div>
    </div>
  </>;
}
