import Link from "next/link";
import {ArrowRight, Gauge, Hourglass, Lock, LogIn} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Callout, Card, Kpi, Meter} from "../../../components/ui";
import {DecisionButtons} from "../../../components/measurement-forms";
import {apiGet, type MeasurementRow} from "../../../lib/api";
import {getDataset} from "../../../lib/data";

export const dynamic = "force-dynamic";
const br = (iso: string | null) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "—");

export default async function MedicoesPortfolio() {
  const data = await getDataset();
  if (data.source !== "api") return <>
    <PageHead title="Medições" subtitle="Avanço físico por serviços e medições aprovadas."/>
    <Callout tone="info" icon={Lock}>As medições são registradas no banco de dados. <a className="link" href="/login"><LogIn size={14}/> Entrar</a></Callout>
  </>;
  const pending = (await apiGet<MeasurementRow[]>("/measurements/pending")) ?? [];
  const works = data.projects.filter(p => p.status !== "COST_POOL");
  const measured = works.filter(p => p.physical);
  return <>
    <PageHead eyebrow="Campo" title="Medições" subtitle="Fila de aprovação e avanço físico de cada obra."/>
    <div className="kpis" style={{gridTemplateColumns: "repeat(3, minmax(0, 1fr))"}}>
      <Kpi label="Aguardando aprovação" value={String(pending.length)} note="medições pendentes em todas as obras" icon={Hourglass} tone="warn"/>
      <Kpi label="Obras com medição" value={measured.length + " de " + works.length} note="com serviços e medições aprovadas" icon={Gauge} tone="ok"/>
      <Kpi label="Avanço médio" value={measured.length ? (measured.reduce((s, p) => s + p.physical!.progress, 0) / measured.length).toLocaleString("pt-BR", {maximumFractionDigits: 1}) + "%" : "—"}
           note="média simples das obras medidas" icon={Gauge} tone="info"/>
    </div>
    <div className="grid-main">
      <Card flush title="Fila de aprovação" subtitle="Ordem de registro">
        {pending.map(m => <div key={m.id} className="list-item">
          <div style={{flex: 1}}><b>{m.project} · {m.service}</b>
            <small>{Number(m.quantity).toLocaleString("pt-BR")} {m.unit} · medido em {br(m.measured_on)} por {m.recorded_by}{m.notes ? " — " + m.notes : ""}</small></div>
          <DecisionButtons projectId={m.project_id} measurementId={m.id}/>
        </div>)}
        {!pending.length && <p className="empty">Nenhuma medição aguardando aprovação.</p>}
      </Card>
      <Card flush title="Avanço por obra" subtitle="Abra a obra para cadastrar serviços e medir">
        {works.map(p => <Link key={p.key} href={p.href + "/medicoes"} className="list-item">
          <div style={{flex: 1}}><b>{p.name}</b>
            {p.physical ? <><div className="meter-label" style={{marginTop: 6}}><span>{p.physical.services} serviços</span>
              <span>{p.physical.progress.toLocaleString("pt-BR")}%</span></div><Meter value={p.physical.progress} tone="var(--ok)"/></>
              : <small>Sem serviços cadastrados</small>}</div>
          <ArrowRight size={16}/>
        </Link>)}
      </Card>
    </div>
  </>;
}
