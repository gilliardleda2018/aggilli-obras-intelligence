import Link from "next/link";
import {AlertTriangle, ArrowRight, Lock, LogIn, MapPin} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Badge, Callout, Meter, type Tone} from "../../../components/ui";
import {getDataset} from "../../../lib/data";
import {money, pct, percent} from "../../../lib/portfolio";

export const dynamic = "force-dynamic";

const STATUS: Record<string, {label: string; tone: Tone | "neutral"}> = {
  PLANNED: {label: "Planejada", tone: "info"}, IN_PROGRESS: {label: "Em execução", tone: "ok"}, PAUSED: {label: "Paralisada", tone: "warn"},
  DONE: {label: "Concluída", tone: "neutral"}, COST_POOL: {label: "A ratear", tone: "warn"},
};

export default async function Obras() {
  const data = await getDataset();
  const projects = [...data.projects].sort((a, b) => Number(a.status === "COST_POOL") - Number(b.status === "COST_POOL")
    || b.contracts.total - a.contracts.total || b.weekly - a.weekly);
  return <>
    {data.error && <div style={{marginBottom: 16}}><Callout icon={AlertTriangle}>{data.error}</Callout></div>}
    <PageHead eyebrow={data.sourceLabel} title="Obras" subtitle="Todas as frentes, com situação, programação da semana, obrigações e contratos."
              actions={data.source === "unavailable" ? <a className="btn primary" href="/login"><LogIn/>Entrar</a> : undefined}/>
    {data.source === "unavailable" && <div style={{marginBottom: 18}}>
      <Callout tone="info" icon={Lock}>As obras ficam no banco de dados, com acesso por empresa e função. Entre para ver e editar
        as obras da sua organização.</Callout></div>}
    <div className="project-grid">
      {projects.map(project => {
        const status = STATUS[project.status] ?? {label: project.status, tone: "neutral" as const};
        return <Link key={project.key} href={project.href} className="card project-card">
          <div className="title">
            <div><h3>{project.name}</h3>{project.municipality && <span className="row-sub"><MapPin size={12}/> {project.municipality}</span>}</div>
            <Badge tone={status.tone}>{status.label}</Badge>
          </div>
          <div className="meta">
            <div><small>Na semana</small><strong>{project.weekly ? money(project.weekly) : "—"}</strong></div>
            <div><small>Em aberto</small><strong>{project.open ? money(project.open) : "—"}</strong></div>
          </div>
          <div>
            {project.physical
              ? <><div className="meter-label"><span>Avanço físico</span><span>{project.physical.progress.toLocaleString("pt-BR")}%</span></div>
                  <Meter value={project.physical.progress} tone="var(--ok)"/></>
              : <><div className="meter-label"><span>Contratos adiantados</span>
                  <span>{project.contracts.total ? percent(project.contracts.advanceValued, project.contracts.total) : "sem contrato"}</span></div>
                  <Meter value={pct(project.contracts.advanceValued, project.contracts.total)}/></>}
          </div>
          <div className="activity">{project.activity ?? "Sem relato de campo."}</div>
          <div className="foot">
            <span className="row-sub">{project.flagged ? project.flagged + " itens a conferir" : project.physical ? "Medição aprovada" : "Sem medição"}</span>
            <ArrowRight size={16}/>
          </div>
        </Link>;
      })}
      {!projects.length && <p className="empty">Nenhuma obra cadastrada para o seu acesso.</p>}
    </div>
  </>;
}
