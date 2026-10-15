import Link from "next/link";
import {ArrowLeft, Lock, Sheet} from "lucide-react";
import {PageHead} from "../../../../../components/app-shell";
import {Callout, Card, Meter} from "../../../../../components/ui";
import {PrintButton} from "../../../../../components/print-button";
import {CostChart, CostSummary, Missing, ProgressChart, ScheduleSummary, modelLabel} from "../../../../../components/forecast-ui";
import {Coverage, Flags, brl, qty} from "../../../../../components/material-ui";
import {apiGet, type AlertsResponse, type MaterialRow, type ProjectIntelligence} from "../../../../../lib/api";
import {money} from "../../../../../lib/portfolio";

export const dynamic = "force-dynamic";
type Details = {name: string; location: string; municipality: string | null; address: string | null; responsible: string | null;
  budget: string | null; start_date: string | null; end_date: string | null};
type Dashboard = {physical_progress: number; planning_complete: boolean; stages: {name: string; progress: number}[]};
const SEVERITY = {high: "Alta", medium: "Média", low: "Baixa"} as const;
const date = (iso: string | null) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "—");

export default async function RelatorioObra({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  const base = "/projects/" + encodeURIComponent(id);
  const back = <Link href="/relatorios" className="back"><ArrowLeft/>Relatórios</Link>;
  const [details, dashboard, intel, materials, alerts] = await Promise.all([
    apiGet<Details>(base + "/details"), apiGet<Dashboard>(base + "/dashboard"), apiGet<ProjectIntelligence>(base + "/intelligence"),
    apiGet<MaterialRow[]>(base + "/materials"), apiGet<AlertsResponse>("/alerts"),
  ]);
  if (!details || !dashboard || !intel) return <>{back}<Callout icon={Lock}>Obra indisponível, sem sessão ou sem autorização.</Callout></>;
  const open = (alerts?.alerts ?? []).filter(a => a.project_id === id && !a.review);
  const generated = new Date().toLocaleString("pt-BR", {timeZone: "America/Fortaleza"});
  return <div className="report">
    <div className="actions" style={{display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8}}>
      {back}
      <div style={{display: "flex", gap: 8}}>
        <a className="btn" href={"/api/download/projects/" + id + "/reports/obra.xlsx"}><Sheet/>Excel</a>
        <PrintButton label="Imprimir / salvar PDF"/>
      </div>
    </div>
    <PageHead eyebrow={"Relatório da obra · gerado em " + generated} title={details.name}
              subtitle={[details.municipality ?? details.location, details.address, details.responsible && "resp. " + details.responsible].filter(Boolean).join(" · ")}/>

    <div className="grid-2">
      <Card title="Prazo" subtitle={modelLabel(intel.schedule.model, intel.schedule.version)}>
        <ScheduleSummary s={intel.schedule}/><Missing items={intel.schedule.missing}/>
        <p className="hint">Contrato: {date(details.start_date)} a {date(details.end_date)}</p>
      </Card>
      <Card title="Custo" subtitle={modelLabel(intel.cost.model, intel.cost.version)}>
        <CostSummary c={intel.cost}/><Missing items={intel.cost.missing}/>
        <p className="hint">Orçamento: {details.budget ? money(Number(details.budget)) : "não informado"} · incorrido {money(intel.cost.actual_cost)}</p>
      </Card>
    </div>

    <div className="grid-2" style={{marginTop: 16}}>
      <Card title="Avanço físico" subtitle="Medido × linha de base × previsão"><ProgressChart data={intel}/></Card>
      <Card title="Custo acumulado" subtitle="Incorrido e projeção"><CostChart data={intel}/></Card>
    </div>

    <div className="stack" style={{marginTop: 16}}>
      <Card title={"Serviços · avanço " + dashboard.physical_progress.toLocaleString("pt-BR") + "%"}
            subtitle={dashboard.planning_complete ? "planejamento completo" : "planejamento incompleto (pesos abaixo de 100%)"}>
        {dashboard.stages.length ? <div className="bars">{dashboard.stages.map(s => <div key={s.name}>
          <div className="meter-label"><span>{s.name}</span><span>{s.progress.toLocaleString("pt-BR")}%</span></div>
          <Meter value={s.progress} tone="var(--ok)"/></div>)}</div> : <p className="empty">Sem serviços medidos.</p>}
      </Card>

      <Card flush title="Materiais" subtitle="Saldo, valor, cobertura e sinais">
        <div className="table-wrap"><table>
          <thead><tr><th>Material</th><th className="num">Saldo</th><th className="num">Valor</th><th className="num">Consumido</th><th>Cobertura</th><th>Situação</th></tr></thead>
          <tbody>{(materials ?? []).map(m => <tr key={m.id}>
            <td><b>{m.name}</b></td><td className="num">{qty(m.balance)} {m.unit}</td><td className="num">{brl(m.stock_value)}</td>
            <td className="num">{qty(m.consumed)} {m.unit}{m.expected_consumption && <span className="cell-sub">esperado {qty(m.expected_consumption)}</span>}</td>
            <td><Coverage days={m.coverage_days}/></td><td><Flags flags={m.flags}/></td></tr>)}
          {!materials?.length && <tr><td colSpan={6} className="empty">Nenhum material controlado.</td></tr>}</tbody>
        </table></div>
      </Card>

      <Card flush title={"Alertas em aberto (" + open.length + ")"} subtitle="Sinais para conferir — não são conclusões">
        <div className="table-wrap"><table>
          <thead><tr><th>Prioridade</th><th>Alerta</th><th>Detalhe</th></tr></thead>
          <tbody>{open.map(a => <tr key={a.key}><td>{SEVERITY[a.severity]}</td><td><b>{a.title}</b></td><td>{a.detail}</td></tr>)}
          {!open.length && <tr><td colSpan={3} className="empty">Nenhum alerta em aberto.</td></tr>}</tbody>
        </table></div>
      </Card>

      <p className="hint">Previsões são estimativas com faixa de incerteza (P10–P90) calculadas a partir das medições aprovadas e dos custos lançados;
        pagamentos programados não são pagamentos confirmados. Aggilli Obras Intelligence.</p>
    </div>
  </div>;
}
