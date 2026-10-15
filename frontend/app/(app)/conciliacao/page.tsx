import {AlertTriangle, BadgeCheck, CalendarClock, ShieldAlert, Truck} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Callout, Card, Kpi} from "../../../components/ui";
import {payroll} from "../../../lib/tuntum-data";
import {compactMoney, money, reconciliation, SOURCE, totals} from "../../../lib/portfolio";

export default function Conciliacao() {
  const t = totals();
  const flagged = payroll.filter(item => item.notes);
  return <>
    <PageHead eyebrow={SOURCE.label} title="Conciliação"
              subtitle="O que foi devido, o que foi programado e o que já tem comprovante — sem presumir quitação."/>
    <div className="kpis">
      <Kpi label="Dívidas de fornecedores" value={money(t.supplierDebt)} note="relatadas · não conciliadas" icon={Truck} tone="warn"/>
      <Kpi label="FOPAG da semana" value={money(t.weekly)} note="programada · não comprovada" icon={CalendarClock}/>
      <Kpi label="Pagamentos confirmados" value="Não informado" note="aguardando comprovantes" icon={BadgeCheck} tone="ok"/>
      <Kpi label="Saldo contratual na planilha" value={compactMoney(t.contractBalance)} note="não é o saldo financeiro global"
           icon={ShieldAlert} tone="info"/>
    </div>
    <div className="grid-2">
      <Card flush title="Divergências entre relato e folha" subtitle="Resolver antes de pagar ou de importar para o sistema">
        {reconciliation.map(item => <div key={item.title} className="list-item">
          <span className="dot-icon tone-warn"><AlertTriangle/></span><div><b>{item.title}</b><small>{item.detail}</small></div>
        </div>)}
      </Card>
      <div className="stack">
        <Card flush title="Lançamentos da FOPAG com observação" subtitle={flagged.length + " itens"}>
          {flagged.map(item => <div key={item.name} className="list-item">
            <div><b>{item.name} · {item.project}</b><small>{item.notes}</small></div>
            <span className="amount">{money(item.amount)}</span>
          </div>)}
        </Card>
        <Callout tone="info" icon={BadgeCheck}>Fluxo previsto no sistema: <b>solicitação → aprovação → programação → pagamento com
          comprovante → baixa do saldo</b>, com rateio entre obras aprovado e trilha de auditoria.</Callout>
      </div>
    </div>
  </>;
}
