import Link from "next/link";
import {
  AlertTriangle, ArrowRight, Banknote, CalendarClock, ChevronRight, FileWarning, Hammer, HardHat, Truck, Wallet,
} from "lucide-react";
import {PageHead} from "../../components/app-shell";
import {PrintButton} from "../../components/print-button";
import {Badge, Callout, Card, Kpi, Meter} from "../../components/ui";
import {byCategory, compactMoney, money, pct, percent, projectSummaries, reconciliation, SOURCE, topPayments, totals} from "../../lib/portfolio";

export default function Overview() {
  const t = totals();
  const projects = projectSummaries().sort((a, b) => b.weekly - a.weekly || b.contractBalance - a.contractBalance);
  const categories = byCategory();
  const maxCategory = Math.max(...categories.map(category => category.amount));
  const payments = topPayments(6);
  return <>
    <PageHead eyebrow={"Tuntum / MA · " + SOURCE.label} title="Central de obras"
              subtitle="Programação semanal, contratos e pendências de todas as frentes em um só lugar."
              actions={<>
                <PrintButton/>
                <Link className="btn primary" href="/fopag"><CalendarClock/>Abrir FOPAG</Link>
              </>}/>

    <div className="kpis">
      <Kpi label="FOPAG da semana" value={money(t.weekly)} note={t.items + " lançamentos · pagamento não confirmado"} icon={CalendarClock}/>
      <Kpi label="Mão de obra" value={money(t.labor)} note={t.laborItems + " lançamentos · " + percent(t.labor, t.weekly) + " da folha"}
           icon={HardHat} tone="info"/>
      <Kpi label="Saldo de contratos" value={compactMoney(t.contractBalance)}
           note={"de " + compactMoney(t.contractTotal) + " contratados"} icon={Wallet} tone="ok"/>
      <Kpi label="Dívidas com fornecedores" value={money(t.supplierDebt)} note={t.suppliers + " fornecedores · a conciliar"}
           icon={Truck} tone="warn"/>
    </div>

    <div className="grid-main">
      <div className="stack">
        <Card flush title="Carteira de obras" subtitle={t.projects + " frentes · ordenadas pela programação da semana"}
              action={<Link className="link" href="/obras">Ver todas<ArrowRight/></Link>}>
          {projects.slice(0, 8).map(project => <Link key={project.slug} href={"/obras/referencia/" + project.slug} className="row">
            <div>
              <div className="row-title">{project.name}</div>
              <div className="row-sub">{project.activity ?? "Sem atividade relatada nesta semana"}</div>
            </div>
            <div className="row-meter">
              <div className="meter-label"><span>Contratos adiantados</span>
                <span>{project.contractTotal ? percent(project.contractAdvance, project.contractTotal) : "—"}</span></div>
              <Meter value={pct(project.contractAdvance, project.contractTotal)}/>
            </div>
            <div className="row-amount">{project.weekly ? money(project.weekly) : "—"}<small>na semana</small></div>
            <ChevronRight className="chev"/>
          </Link>)}
        </Card>

        <Card title="Para onde vai a folha" subtitle="Distribuição da FOPAG por categoria">
          <div className="bars">
            {categories.map(category => <div key={category.category} className="bar-row">
              <span>{category.category}</span>
              <Meter value={pct(category.amount, maxCategory)}/>
              <b>{money(category.amount)}</b>
            </div>)}
          </div>
        </Card>
      </div>

      <div className="stack">
        <Card flush title="Maiores pagamentos programados" subtitle="Semana de referência · aguardando comprovante"
              action={<Link className="link" href="/fopag">FOPAG<ArrowRight/></Link>}>
          {payments.map(item => <div key={item.name + item.project} className="list-item">
            <span className="dot-icon tone-brand">{item.category === "Mão de obra" ? <Hammer/> : <Banknote/>}</span>
            <div><b>{item.name}</b><small>{item.project}</small></div>
            <span className="amount">{money(item.amount)}</span>
          </div>)}
        </Card>

        <Card flush title="Pendências de conciliação" subtitle={reconciliation.length + " divergências entre relato e folha"}
              action={<Link className="link" href="/conciliacao">Revisar<ArrowRight/></Link>}>
          {reconciliation.slice(0, 4).map(item => <div key={item.title} className="list-item">
            <span className="dot-icon tone-warn"><AlertTriangle/></span>
            <div><b>{item.title}</b><small>{item.detail}</small></div>
          </div>)}
        </Card>

        <Callout icon={FileWarning}>
          <b>Avanço físico ainda não medido.</b> Os percentuais de obra aparecem depois do cadastro dos serviços e da aprovação das
          medições; pagamentos não são usados para estimar avanço. <Badge tone="neutral">Medições em breve</Badge>
        </Callout>
      </div>
    </div>

    <footer className="footer"><span>Aggilli Obras Intelligence</span><span>{SOURCE.label} · {SOURCE.detail}</span></footer>
  </>;
}
