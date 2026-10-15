import Link from "next/link";
import {AlertTriangle, ArrowLeft, Gauge, Lock, Receipt, Wallet} from "lucide-react";
import {PageHead} from "../../../../components/app-shell";
import {Callout, Card, Kpi, Meter} from "../../../../components/ui";
import {accessToken} from "../../../../lib/session";
import {money} from "../../../../lib/portfolio";

const API = process.env.API_BASE_URL || "http://localhost:8000";
type Data = {name: string; location: string; budget: string; physical_progress: number; planning_complete: boolean;
  stages: {name: string; progress: number; approved_quantity: string; planned_quantity: string; unit: string}[]};

export default async function Detail({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  const token = await accessToken();
  if (!token) return <><Link href="/obras" className="back"><ArrowLeft/>Obras</Link>
    <Callout tone="info" icon={Lock}>Autenticação necessária. <a className="link" href="/api/auth/login">Entrar</a></Callout></>;
  let data: Data | null = null;
  try {
    const response = await fetch(API + "/api/v1/projects/" + encodeURIComponent(id) + "/dashboard",
      {headers: {Authorization: "Bearer " + token}, cache: "no-store"});
    if (response.ok) data = await response.json();
  } catch {}
  if (!data) return <><Link href="/obras" className="back"><ArrowLeft/>Obras</Link>
    <Callout icon={Lock}>Obra indisponível ou acesso não autorizado.</Callout></>;
  return <>
    <Link href="/obras" className="back"><ArrowLeft/>Obras</Link>
    <PageHead eyebrow="Obra cadastrada" title={data.name} subtitle={data.location}
              actions={<Link className="btn primary" href={"/operacao/" + id}><Receipt/>Despesas e pagamentos</Link>}/>
    <div className="kpis" style={{gridTemplateColumns: "repeat(3, minmax(0, 1fr))"}}>
      <Kpi label="Avanço físico" value={data.physical_progress.toLocaleString("pt-BR") + "%"} note="medições aprovadas" icon={Gauge}/>
      <Kpi label="Orçamento previsto" value={money(Number(data.budget))} note="valor contratual" icon={Wallet} tone="info"/>
      <Kpi label="Serviços" value={String(data.stages.length)} note={data.planning_complete ? "pesos somam 100%" : "planejamento incompleto"}
           icon={AlertTriangle} tone={data.planning_complete ? "ok" : "warn"}/>
    </div>
    {!data.planning_complete && <div style={{marginBottom: 18}}><Callout icon={AlertTriangle}>Planejamento incompleto: os pesos dos
      serviços não somam 100%, então o avanço físico ainda não representa a obra inteira.</Callout></div>}
    <Card flush title="Serviços e medições" subtitle="Quantidades aprovadas sobre o previsto">
      {data.stages.length ? data.stages.map(stage => <div key={stage.name} className="list-item">
        <div style={{flex: 1}}><b>{stage.name}</b>
          <div className="meter-label" style={{marginTop: 6}}><span>{stage.approved_quantity} / {stage.planned_quantity} {stage.unit}</span>
            <span>{stage.progress}%</span></div>
          <Meter value={stage.progress}/></div>
      </div>) : <p className="empty">Nenhum serviço cadastrado.</p>}
    </Card>
  </>;
}
