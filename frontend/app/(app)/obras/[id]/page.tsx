import Link from "next/link";
import {AlertTriangle, ArrowLeft, CalendarClock, ClipboardList, Gauge, Lock, MapPin, Receipt, Scale, Wallet} from "lucide-react";
import {PageHead} from "../../../../components/app-shell";
import {Badge, Callout, Card, Kpi, Meter} from "../../../../components/ui";
import {accessToken} from "../../../../lib/session";
import {getDataset} from "../../../../lib/data";
import {money, pct, percent, sum} from "../../../../lib/portfolio";
import {ProjectForm, type ProjectDetails} from "./project-form";
import {apiGet, type ProjectIntelligence} from "../../../../lib/api";
import {CostChart, CostSummary, Probability, ProgressChart, ScheduleSummary, br, modelLabel} from "../../../../components/forecast-ui";

export const dynamic = "force-dynamic";
const API = process.env.API_BASE_URL || "http://localhost:8000";
type Dashboard = {physical_progress: number; planning_complete: boolean;
  stages: {name: string; progress: number; approved_quantity: string; planned_quantity: string; unit: string}[]};

async function get<T>(path: string, token: string): Promise<T | null> {
  try {
    const response = await fetch(API + "/api/v1" + path, {headers: {Authorization: "Bearer " + token}, cache: "no-store"});
    return response.ok ? await response.json() : null;
  } catch {
    return null;
  }
}

export default async function Detail({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  const back = <Link href="/obras" className="back"><ArrowLeft/>Obras</Link>;
  const token = await accessToken();
  if (!token) return <>{back}<Callout tone="info" icon={Lock}>Autenticação necessária. <a className="link" href="/login">Entrar</a></Callout></>;
  const [details, dashboard, data, intel] = await Promise.all([
    get<ProjectDetails & {name: string; location: string; source: string | null}>("/projects/" + encodeURIComponent(id) + "/details", token),
    get<Dashboard>("/projects/" + encodeURIComponent(id) + "/dashboard", token),
    getDataset(),
    apiGet<ProjectIntelligence>("/projects/" + encodeURIComponent(id) + "/intelligence"),
  ]);
  if (!details || !dashboard) return <>{back}<Callout icon={Lock}>Obra indisponível ou acesso não autorizado.</Callout></>;
  const row = data.projects.find(project => project.key === id);
  const week = data.schedule.filter(item => item.projectHref === "/obras/" + id);
  const contracts = data.contracts.filter(contract => contract.projectHref === "/obras/" + id);
  const payables = data.payables.filter(payable => payable.project === details.name);
  const measured = dashboard.stages.length > 0;
  return <>
    {back}
    <PageHead eyebrow={(details.municipality ?? details.location) + (details.source ? " · origem: " + details.source : "")} title={details.name}
              subtitle={details.address ?? "Endereço não informado"}
              actions={<><Link className="btn" href={"/obras/" + id + "/medicoes"}><ClipboardList/>Medições</Link>
                <Link className="btn primary" href={"/operacao/" + id}><Receipt/>Despesas e pagamentos</Link></>}/>
    <div className="kpis">
      <Kpi label="Avanço físico" value={measured ? dashboard.physical_progress.toLocaleString("pt-BR") + "%" : "Sem medição"}
           note={measured ? (dashboard.planning_complete ? "medições aprovadas" : "planejamento incompleto") : "cadastre serviços e aprove medições"}
           icon={Gauge} tone={measured ? "ok" : "warn"}/>
      <Kpi label="Orçamento contratual" value={details.budget ? money(Number(details.budget)) : "Não informado"}
           note={details.budget ? "valor da obra" : "informe nos dados da obra"} icon={Wallet} tone="info"/>
      <Kpi label="Programado na semana" value={money(sum(week.map(item => item.amount)))} note={week.length + " lançamentos · " + data.weekLabel}
           icon={CalendarClock}/>
      <Kpi label="Em aberto" value={money(sum(payables.map(p => p.outstanding)))} note={payables.length + " despesas sem pagamento comprovado"}
           icon={Scale} tone="warn"/>
    </div>

    {intel && <div className="stack" style={{marginBottom: 18}}>
      <div className="grid-2">
        <Card title="Término provável" subtitle={modelLabel(intel.schedule.model, intel.schedule.version)}
              action={<Probability value={intel.schedule.probability_on_time}/>}>
          <ScheduleSummary s={intel.schedule}/>
          {intel.schedule.status === "ok" && <ul className="missing" style={{marginTop: 10}}>
            <li>Produtividade média {intel.schedule.productivity!.average_pp_per_week.toLocaleString("pt-BR")} p.p./semana · recente{" "}
              {intel.schedule.productivity!.recent_pp_per_week.toLocaleString("pt-BR")}</li>
            {intel.schedule.earned_schedule?.spi_t && <li>Earned Schedule: SPI(t) {intel.schedule.earned_schedule.spi_t.toLocaleString("pt-BR")} ·
              previsto pelo método {br(intel.schedule.earned_schedule.ieac_finish)}</li>}
            {intel.schedule.factors?.map(f => <li key={f}>{f}</li>)}
            {!!intel.schedule.critical_services?.length && <li>Serviços críticos: {intel.schedule.critical_services.map(c => c.name + " (" +
              c.progress.toLocaleString("pt-BR") + "%)").join(", ")}</li>}
            {intel.schedule.backtest && <li>Retroteste: previu {intel.schedule.backtest.predicted_last_progress.toLocaleString("pt-BR")}% para a última
              medição; real {intel.schedule.backtest.actual_last_progress.toLocaleString("pt-BR")}%</li>}
          </ul>}
        </Card>
        <Card title="Custo final estimado" subtitle={modelLabel(intel.cost.model, intel.cost.version)}>
          <CostSummary c={intel.cost}/>
          {intel.cost.status === "ok" && <ul className="missing" style={{marginTop: 10}}>
            {intel.cost.earned_value !== undefined && <li>Valor agregado {money(intel.cost.earned_value)} · custo real {money(intel.cost.actual_cost)}
              {intel.cost.spi ? " · SPI " + intel.cost.spi.toLocaleString("pt-BR") : ""}</li>}
            {intel.cost.vac !== undefined && <li>{intel.cost.vac < 0 ? "Estouro" : "Folga"} projetado: {money(Math.abs(intel.cost.vac))}</li>}
            {intel.cost.factors?.map(f => <li key={f}>{f}</li>)}
          </ul>}
        </Card>
      </div>
      <div className="grid-2">
        <Card title="Evolução do avanço físico" subtitle="Medido × linha de base × previsão"><ProgressChart data={intel}/></Card>
        <Card title="Evolução do custo" subtitle="Incorrido acumulado e projeção do custo final"><CostChart data={intel}/></Card>
      </div>
      <Card flush title="Como a previsão mudou" subtitle="Cada recálculo fica guardado com modelo e versão">
        <div className="table-wrap"><table>
          <thead><tr><th>Quando</th><th>Previsão</th><th>Resultado</th><th>Modelo</th></tr></thead>
          <tbody>{intel.history.slice(0, 10).map((h, i) => <tr key={i}>
            <td>{new Date(h.created_at).toLocaleString("pt-BR", {dateStyle: "short", timeStyle: "short"})}</td>
            <td>{h.kind === "schedule" ? "Término" : "Custo final"}</td>
            <td>{h.status !== "ok" ? <span className="cell-sub">dados insuficientes</span> : h.kind === "schedule"
              ? br(String(h.summary.finish_p50)) + " (" + Math.round(Number(h.summary.probability_on_time ?? 0) * 100) + "% no prazo, avanço " + h.summary.current_progress + "%)"
              : money(Number(h.summary.eac_p50)) + " (gasto " + money(Number(h.summary.actual_cost)) + ")"}</td>
            <td className="model-tag">{h.model} v{h.version}</td>
          </tr>)}</tbody>
        </table></div>
      </Card>
    </div>}

    <div className="grid-2">
      <div className="stack">
        <Card flush title="Pagamentos da semana" subtitle={data.weekLabel}>
          {week.map(item => <div key={item.key} className="list-item">
            <div><b>{item.supplier}</b><small>{item.work}</small>{item.notes && <div className="note"><AlertTriangle/>{item.notes}</div>}</div>
            <span className="amount">{money(item.amount)}</span>
          </div>)}
          {!week.length && <p className="empty">Nenhum pagamento programado nesta semana.</p>}
        </Card>
        <Card flush title="Serviços e medições" subtitle="Quantidades aprovadas sobre o previsto">
          {dashboard.stages.map(stage => <div key={stage.name} className="list-item">
            <div style={{flex: 1}}><b>{stage.name}</b>
              <div className="meter-label" style={{marginTop: 6}}><span>{stage.approved_quantity} / {stage.planned_quantity} {stage.unit}</span>
                <span>{stage.progress.toLocaleString("pt-BR")}%</span></div>
              <Meter value={stage.progress} tone="var(--ok)"/></div>
          </div>)}
          {!measured && <p className="empty">Nenhum serviço cadastrado. O avanço físico só aparece com serviços e medições aprovadas.
            <br/><Link className="link" href={"/obras/" + id + "/medicoes"}>Cadastrar serviços e medir</Link></p>}
        </Card>
      </div>
      <div className="stack">
        <Card flush title="Contratos de mão de obra" subtitle={contracts.length + " contratos · valores informados na fonte"}>
          {contracts.map(contract => <div key={contract.contractor} className="list-item">
            <div style={{flex: 1}}><b>{contract.contractor}</b>
              {contract.total
                ? <><div className="meter-label" style={{marginTop: 6}}><span>{money(contract.advance ?? 0)} de {money(contract.total)}</span>
                    <span>{percent(contract.advance ?? 0, contract.total)}</span></div><Meter value={pct(contract.advance ?? 0, contract.total)}/></>
                : <small>Sem valor de contrato · adiantado {money(contract.advance ?? 0)}</small>}</div>
            <span className="amount">{contract.balance === null ? "—" : money(contract.balance)}<small className="cell-sub">saldo</small></span>
          </div>)}
          {!contracts.length && <p className="empty">Nenhum contrato registrado.</p>}
        </Card>
        {row?.activity && <Card title="Último relato de campo"><p>{row.activity}</p></Card>}
      </div>
    </div>

    <div style={{marginTop: 18}}>
      <Card title="Dados da obra" subtitle="Situação, responsável, orçamento, prazos e localização"
            action={details.latitude ? <Badge tone="ok"><MapPin size={12}/> Localizada</Badge> : <Badge tone="warn">Sem coordenadas</Badge>}>
        <ProjectForm id={id} details={details}/>
      </Card>
    </div>
  </>;
}
