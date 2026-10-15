import Link from "next/link";
import {notFound} from "next/navigation";
import {AlertTriangle, ArrowLeft, CalendarClock, FileSignature, HardHat, Wallet} from "lucide-react";
import {PageHead} from "../../../../../components/app-shell";
import {Callout, Card, Kpi, Meter} from "../../../../../components/ui";
import {contracts, payroll} from "../../../../../lib/tuntum-data";
import {money, pct, percent, projectBySlug, projectSummaries, SOURCE} from "../../../../../lib/portfolio";

export function generateStaticParams() {
  return projectSummaries().map(project => ({slug: project.slug}));
}

export default async function ReferenceProject({params}: {params: Promise<{slug: string}>}) {
  const {slug} = await params;
  const name = projectBySlug(slug);
  if (!name) notFound();
  const summary = projectSummaries().find(project => project.slug === slug)!;
  const items = payroll.filter(item => item.project === name);
  const own = contracts.filter(contract => contract.project === name);
  return <>
    <Link href="/obras" className="back"><ArrowLeft/>Obras</Link>
    <PageHead eyebrow={SOURCE.label + " · referência"} title={name} subtitle={summary.activity ?? "Sem atividade relatada nesta semana."}
              actions={<Link className="btn" href={"/fopag?obra=" + slug}><CalendarClock/>Ver na FOPAG</Link>}/>
    <div className="kpis">
      <Kpi label="Programado na semana" value={summary.weekly ? money(summary.weekly) : "—"} note={items.length + " lançamentos"} icon={CalendarClock}/>
      <Kpi label="Contratado" value={summary.contractTotal ? money(summary.contractTotal) : "—"} note={own.length + " contratos"}
           icon={FileSignature} tone="info"/>
      <Kpi label="Adiantado" value={summary.contractAdvance ? money(summary.contractAdvance) : "—"}
           note={summary.contractTotal ? percent(summary.contractAdvance, summary.contractTotal) + " do contratado" : "sem contrato"} icon={Wallet} tone="ok"/>
      <Kpi label="Avanço físico" value="Sem medição" note="cadastre serviços e aprove medições" icon={HardHat} tone="warn"/>
    </div>
    <div className="grid-2">
      <Card flush title="Lançamentos da semana" subtitle="FOPAG · aguardando comprovante">
        {items.length ? items.map(item => <div key={item.name + item.work} className="list-item">
          <div><b>{item.name}</b><small>{item.work}</small>{item.notes && <div className="note"><AlertTriangle/>{item.notes}</div>}</div>
          <span className="amount">{money(item.amount)}</span>
        </div>) : <p className="empty">Nenhum lançamento desta obra na semana.</p>}
      </Card>
      <Card flush title="Contratos de mão de obra" subtitle="Valores da planilha, a conferir">
        {own.length ? own.map(contract => <div key={contract.name} className="list-item">
          <div style={{flex: 1}}><b>{contract.name}</b>
            <div className="meter-label" style={{marginTop: 6}}><span>{money(contract.advance)} de {money(contract.total)}</span>
              <span>{percent(contract.advance, contract.total)}</span></div>
            <Meter value={pct(contract.advance, contract.total)}/></div>
          <span className="amount">{money(contract.balance)}<small>saldo</small></span>
        </div>) : <p className="empty">Nenhum contrato desta obra na folha.</p>}
      </Card>
    </div>
    <div style={{marginTop: 18}}>
      <Callout icon={AlertTriangle}>Esta é uma página de referência, gerada a partir da importação da {SOURCE.label}. Para registrar despesas,
        pagamentos e medições, a obra precisa ser cadastrada no sistema.</Callout>
    </div>
  </>;
}
