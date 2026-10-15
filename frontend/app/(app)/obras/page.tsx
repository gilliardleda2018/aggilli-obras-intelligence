import Link from "next/link";
import {ArrowRight, Building2, Lock, LogIn} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Badge, Callout, Card, Meter} from "../../../components/ui";
import {accessToken} from "../../../lib/session";
import {money, pct, percent, projectSummaries, SOURCE} from "../../../lib/portfolio";

const API = process.env.API_BASE_URL || "http://localhost:8000";
type ApiProject = {id: string; name: string; location: string; budget: string};

async function registeredProjects(): Promise<{projects: ApiProject[]; state: "anonymous" | "ok" | "error"}> {
  const token = await accessToken();
  if (!token) return {projects: [], state: "anonymous"};
  try {
    const response = await fetch(API + "/api/v1/projects", {headers: {Authorization: "Bearer " + token}, cache: "no-store"});
    return response.ok ? {projects: await response.json(), state: "ok"} : {projects: [], state: "error"};
  } catch {
    return {projects: [], state: "error"};
  }
}

export default async function Obras() {
  const registered = await registeredProjects();
  const portfolio = projectSummaries().sort((a, b) => b.contractTotal - a.contractTotal || b.weekly - a.weekly);
  return <>
    <PageHead eyebrow="Carteira" title="Obras" subtitle="Todas as frentes de serviço, com contratos, programação da semana e atividade."/>

    <div className="stack">
      <Card title="Obras cadastradas no sistema" subtitle="Dados persistidos, com acesso por empresa e função"
            action={registered.state === "anonymous" ? <a className="btn primary" href="/api/auth/login"><LogIn/>Entrar</a> : undefined}>
        {registered.state === "anonymous" && <Callout tone="info" icon={Lock}>Entre com sua identidade corporativa para ver e editar as obras
          cadastradas. A carteira abaixo vem da importação de referência.</Callout>}
        {registered.state === "error" && <Callout icon={Lock}>Não foi possível carregar as obras autorizadas. Verifique a conexão com a API.</Callout>}
        {registered.state === "ok" && (registered.projects.length
          ? <div className="project-grid">{registered.projects.map(project => <Link key={project.id} href={"/obras/" + project.id}
              className="card project-card">
              <div className="title"><h3>{project.name}</h3><Badge tone="ok">Cadastrada</Badge></div>
              <div className="activity">{project.location}</div>
              <div className="foot"><span>Orçamento {money(Number(project.budget))}</span><ArrowRight/></div>
            </Link>)}</div>
          : <p className="empty">Nenhuma obra cadastrada para o seu acesso.</p>)}
      </Card>

      <div>
        <div className="page-head" style={{marginBottom: 12}}>
          <div><h1 style={{fontSize: 18}}>Carteira importada</h1><p>{portfolio.length} frentes · {SOURCE.label} · {SOURCE.detail}</p></div>
        </div>
        <div className="project-grid">
          {portfolio.map(project => <Link key={project.slug} href={"/obras/referencia/" + project.slug} className="card project-card">
            <div className="title">
              <h3>{project.name}</h3>
              {project.flagged ? <Badge tone="warn">{project.flagged} a conferir</Badge> : <Badge tone="neutral">Sem medição</Badge>}
            </div>
            <div className="meta">
              <div><small>Na semana</small><strong>{project.weekly ? money(project.weekly) : "—"}</strong></div>
              <div><small>Saldo de contratos</small><strong>{project.contractTotal ? money(project.contractBalance) : "—"}</strong></div>
            </div>
            <div>
              <div className="meter-label"><span>Contratos adiantados</span>
                <span>{project.contractTotal ? percent(project.contractAdvance, project.contractTotal) : "—"}</span></div>
              <Meter value={pct(project.contractAdvance, project.contractTotal)}/>
            </div>
            <div className="activity">{project.activity ?? "Sem atividade relatada nesta semana."}</div>
            <div className="foot"><span className="row-sub"><Building2 size={14}/> {project.weeklyItems} lançamentos</span><ArrowRight size={16}/></div>
          </Link>)}
        </div>
      </div>
    </div>
  </>;
}
