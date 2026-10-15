import Link from "next/link";
import {ArrowLeft, ClipboardCheck, Gauge, Hourglass, Layers, Lock} from "lucide-react";
import {PageHead} from "../../../../../components/app-shell";
import {Badge, Callout, Card, Kpi, Meter} from "../../../../../components/ui";
import {DecisionButtons, MeasurementForm, ServiceForm} from "../../../../../components/measurement-forms";
import {apiGet, type MeasurementRow, type ServiceRow} from "../../../../../lib/api";

export const dynamic = "force-dynamic";
const STATUS = {PENDING: {label: "Pendente", tone: "warn"}, APPROVED: {label: "Aprovada", tone: "ok"}, REJECTED: {label: "Recusada", tone: "danger"}} as const;
const br = (iso: string | null) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "—");
const num = (value: string) => Number(value).toLocaleString("pt-BR", {maximumFractionDigits: 3});

export default async function Medicoes({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  const back = <Link href={"/obras/" + id} className="back"><ArrowLeft/>Obra</Link>;
  const [details, services, measurements, dashboard] = await Promise.all([
    apiGet<{name: string}>("/projects/" + encodeURIComponent(id) + "/details"),
    apiGet<{services: ServiceRow[]; weight_total: string; weight_available: string}>("/projects/" + encodeURIComponent(id) + "/services"),
    apiGet<MeasurementRow[]>("/projects/" + encodeURIComponent(id) + "/measurements"),
    apiGet<{physical_progress: number; planning_complete: boolean}>("/projects/" + encodeURIComponent(id) + "/dashboard"),
  ]);
  if (!details || !services || !measurements || !dashboard)
    return <>{back}<Callout icon={Lock}>Obra indisponível, sem sessão ou sem autorização.</Callout></>;
  const pending = measurements.filter(m => m.status === "PENDING");
  return <>
    {back}
    <PageHead eyebrow="Medições" title={details.name} subtitle="Serviços com peso, quantidades executadas e aprovação — a base do avanço físico."/>
    <div className="kpis">
      <Kpi label="Avanço físico" value={services.services.length ? dashboard.physical_progress.toLocaleString("pt-BR") + "%" : "Sem medição"}
           note="pela soma ponderada das medições aprovadas" icon={Gauge} tone="ok"/>
      <Kpi label="Planejamento" value={Number(services.weight_total).toLocaleString("pt-BR") + "%"}
           note={dashboard.planning_complete ? "pesos completos" : "faltam " + Number(services.weight_available).toLocaleString("pt-BR") + "% de peso"}
           icon={Layers} tone={dashboard.planning_complete ? "ok" : "warn"}/>
      <Kpi label="Serviços" value={String(services.services.length)} note="com quantidade prevista" icon={ClipboardCheck} tone="info"/>
      <Kpi label="Aguardando aprovação" value={String(pending.length)} note="medições pendentes" icon={Hourglass} tone="warn"/>
    </div>

    {!dashboard.planning_complete && services.services.length > 0 && <div style={{marginBottom: 18}}>
      <Callout icon={Layers}>Os pesos somam {Number(services.weight_total).toLocaleString("pt-BR")}%. Enquanto não chegarem a 100%, o avanço
        representa apenas os serviços cadastrados.</Callout></div>}

    <div className="grid-main">
      <div className="stack">
        <Card flush title="Serviços" subtitle="Executado aprovado sobre o previsto">
          {services.services.map(service => <div key={service.id} className="list-item">
            <div style={{flex: 1}}>
              <b>{service.name} <span className="cell-sub" style={{display: "inline"}}>· peso {Number(service.weight).toLocaleString("pt-BR")}%</span></b>
              <div className="meter-label" style={{marginTop: 6}}>
                <span>{num(service.approved_quantity)} de {num(service.planned_quantity)} {service.unit}
                  {Number(service.pending_quantity) > 0 && " · " + num(service.pending_quantity) + " pendente"}</span>
                <span>{service.progress.toLocaleString("pt-BR")}%</span></div>
              <Meter value={service.progress} tone="var(--ok)"/>
            </div>
          </div>)}
          {!services.services.length && <p className="empty">Cadastre os serviços da obra para começar a medir.</p>}
        </Card>

        <Card flush title="Aguardando aprovação" subtitle="Engenheiro, fiscal ou administrador decide">
          {pending.map(m => <div key={m.id} className="list-item">
            <div style={{flex: 1}}><b>{m.service} · {num(m.quantity)} {m.unit}</b>
              <small>Medido em {br(m.measured_on)} por {m.recorded_by}{m.notes ? " — " + m.notes : ""}</small></div>
            <DecisionButtons projectId={id} measurementId={m.id}/>
          </div>)}
          {!pending.length && <p className="empty">Nenhuma medição pendente.</p>}
        </Card>

        <Card flush title="Histórico" subtitle="Todas as medições com decisão e responsável">
          <div className="table-wrap"><table>
            <thead><tr><th>Data</th><th>Serviço</th><th className="num">Quantidade</th><th>Situação</th><th>Decisão</th></tr></thead>
            <tbody>{measurements.map(m => <tr key={m.id}>
              <td>{br(m.measured_on)}</td>
              <td><b>{m.service}</b>{m.notes && <span className="cell-sub">{m.notes}</span>}</td>
              <td className="num">{num(m.quantity)} {m.unit}</td>
              <td><Badge tone={STATUS[m.status].tone}>{STATUS[m.status].label}</Badge></td>
              <td>{m.decided_by ? <>{m.decided_by} em {br(m.decided_at)}{m.decision_reason && <span className="cell-sub">{m.decision_reason}</span>}</> : "—"}</td>
            </tr>)}
            {!measurements.length && <tr><td colSpan={5} className="empty">Nenhuma medição registrada.</td></tr>}</tbody>
          </table></div>
        </Card>
      </div>
      <div className="stack">
        <Card title="Registrar medição" subtitle="Quantidade executada no período">
          <MeasurementForm projectId={id} services={services.services}/>
        </Card>
        <Card title="Novo serviço" subtitle="Item do planejamento com unidade, quantidade e peso">
          <ServiceForm projectId={id} available={Number(services.weight_available).toLocaleString("pt-BR")}/>
        </Card>
      </div>
    </div>
  </>;
}
