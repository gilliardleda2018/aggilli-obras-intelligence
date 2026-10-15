import Link from "next/link";
import {
  AlertTriangle, ArrowRight, Banknote, CalendarClock, ChevronRight, FileWarning, Hammer, HardHat, Scale, Wallet,
} from "lucide-react";
import {PageHead} from "../../components/app-shell";
import {PrintButton} from "../../components/print-button";
import {Badge, Callout, Card, Kpi, Meter} from "../../components/ui";
import {getDataset, summarize} from "../../lib/data";
import {compactMoney, money, pct, percent, reconciliation, sum} from "../../lib/portfolio";

export const dynamic = "force-dynamic";

export default async function Overview() {
  const data = await getDataset();
  const t = summarize(data);
  const projects = data.projects.filter(p => p.status !== "COST_POOL").sort((a, b) => b.weekly - a.weekly || b.open - a.open);
  const categories = Array.from(new Set(data.schedule.map(row => row.category)))
    .map(category => ({category, amount: sum(data.schedule.filter(row => row.category === category).map(row => row.amount))}))
    .sort((a, b) => b.amount - a.amount);
  const maxCategory = Math.max(1, ...categories.map(category => category.amount));
  const payments = [...data.schedule].sort((a, b) => b.amount - a.amount).slice(0, 6);
  const flagged = data.schedule.filter(row => row.notes);
  return <>
    {data.error && <div style={{marginBottom: 16}}><Callout icon={AlertTriangle}>{data.error}</Callout></div>}
    <PageHead eyebrow={data.sourceLabel + " · " + data.weekLabel} title="Central de obras"
              subtitle="Programação da semana, obrigações, contratos e pendências de todas as frentes."
              actions={<><PrintButton/><Link className="btn primary" href="/fopag"><CalendarClock/>Abrir FOPAG</Link></>}/>

    <div className="kpis">
      <Kpi label="Programado na semana" value={money(t.weekly)}
           note={t.items + " lançamentos · " + (t.paid ? money(t.paid) + " pagos" : "nenhum pagamento comprovado")} icon={CalendarClock}/>
      <Kpi label="Mão de obra" value={money(t.labor)} note={t.laborItems + " lançamentos · " + percent(t.labor, t.weekly) + " da semana"}
           icon={HardHat} tone="info"/>
      <Kpi label="Obrigações em aberto" value={compactMoney(t.open)} note="despesas registradas ainda não pagas" icon={Scale} tone="warn"/>
      <Kpi label="Saldo de contratos" value={compactMoney(t.contractBalance)}
           note={t.contractCount + " contratos · " + compactMoney(t.contractTotal) + " contratados"} icon={Wallet} tone="ok"/>
    </div>

    <div className="grid-main">
      <div className="stack">
        <Card flush title="Carteira de obras" subtitle={t.projects + " obras · " + t.measured + " com medição aprovada"}
              action={<Link className="link" href="/obras">Ver todas<ArrowRight/></Link>}>
          {projects.slice(0, 8).map(project => <Link key={project.key} href={project.href} className="row">
            <div>
              <div className="row-title">{project.name}</div>
              <div className="row-sub">{project.activity ?? "Sem relato de campo"}</div>
            </div>
            <div className="row-meter">
              {project.physical
                ? <><div className="meter-label"><span>Avanço físico</span><span>{project.physical.progress.toLocaleString("pt-BR")}%</span></div>
                    <Meter value={project.physical.progress} tone="var(--ok)"/></>
                : <><div className="meter-label"><span>Contratos adiantados</span>
                    <span>{project.contracts.total ? percent(project.contracts.advanceValued, project.contracts.total) : "—"}</span></div>
                    <Meter value={pct(project.contracts.advanceValued, project.contracts.total)}/></>}
            </div>
            <div className="row-amount">{project.weekly ? money(project.weekly) : "—"}<small>na semana</small></div>
            <ChevronRight className="chev"/>
          </Link>)}
          {!projects.length && <p className="empty">Nenhuma obra cadastrada.</p>}
        </Card>

        <Card title="Para onde vai o dinheiro da semana" subtitle="Programação por categoria">
          <div className="bars">
            {categories.map(category => <div key={category.category} className="bar-row">
              <span>{category.category}</span><Meter value={pct(category.amount, maxCategory)}/><b>{money(category.amount)}</b>
            </div>)}
            {!categories.length && <p className="empty">Sem pagamentos programados.</p>}
          </div>
        </Card>
      </div>

      <div className="stack">
        <Card flush title="Maiores pagamentos programados" subtitle={data.weekLabel}
              action={<Link className="link" href="/fopag">FOPAG<ArrowRight/></Link>}>
          {payments.map(item => <div key={item.key} className="list-item">
            <span className="dot-icon tone-brand">{item.category === "Mão de obra" ? <Hammer/> : <Banknote/>}</span>
            <div><b>{item.supplier}</b><small>{item.project}</small></div>
            <span className="amount">{money(item.amount)}</span>
          </div>)}
        </Card>

        <Card flush title="Pendências de conciliação"
              subtitle={data.source === "api" ? flagged.length + " lançamentos com observação" : reconciliation.length + " divergências entre relato e folha"}
              action={<Link className="link" href="/conciliacao">Revisar<ArrowRight/></Link>}>
          {(data.source === "api"
            ? flagged.slice(0, 4).map(row => ({title: row.supplier + " · " + row.project, detail: row.notes!}))
            : reconciliation.slice(0, 4)).map(item => <div key={item.title} className="list-item">
            <span className="dot-icon tone-warn"><AlertTriangle/></span><div><b>{item.title}</b><small>{item.detail}</small></div>
          </div>)}
        </Card>

        {t.measured === 0 && <Callout icon={FileWarning}>
          <b>Avanço físico ainda não medido.</b> Os percentuais aparecem depois do cadastro dos serviços e da aprovação das medições;
          pagamentos não são usados para estimar avanço. <Badge tone="neutral">Medições</Badge>
        </Callout>}
      </div>
    </div>

    <footer className="footer"><span>Aggilli Obras Intelligence</span><span>{data.sourceLabel} · {data.weekLabel}</span></footer>
  </>;
}
