import {AlertOctagon, Info, Lock, LogIn, MapPin, MapPinOff} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {PortfolioMap} from "../../../components/portfolio-map";
import {Callout, Kpi} from "../../../components/ui";
import {apiGet, type MapProject} from "../../../lib/api";

export const dynamic = "force-dynamic";

export default async function Mapa() {
  const data = await apiGet<{projects: MapProject[]; maps_configured: boolean}>("/map/projects");
  if (!data) return <>
    <PageHead title="Mapa" subtitle="Onde estão as obras, como andam e qual o risco."/>
    <Callout tone="info" icon={Lock}>Entre para ver o mapa. <a className="link" href="/login"><LogIn size={14}/> Entrar</a></Callout>
  </>;
  const located = data.projects.filter(p => p.location.latitude !== null).length;
  const high = data.projects.filter(p => p.risk.level === "alto").length;
  return <>
    <PageHead eyebrow="Visão" title="Mapa das obras"
              subtitle="Cada marcador mostra situação, avanço físico e o risco calculado pelas previsões de prazo e custo. Clique para abrir o painel da obra."/>
    <div className="kpis">
      <Kpi label="Obras" value={String(data.projects.length)} note="que você pode ver" icon={MapPin}/>
      <Kpi label="No mapa" value={String(located)} note="com localização confirmada" icon={MapPin} tone="ok"/>
      <Kpi label="Sem localização" value={String(data.projects.length - located)} note="defina pelo endereço, mapa ou GPS" icon={MapPinOff}
           tone={located < data.projects.length ? "warn" : "ok"}/>
      <Kpi label="Risco alto" value={String(high)} note="prazo ou custo" icon={AlertOctagon} tone={high ? "danger" : "ok"}/>
    </div>
    <PortfolioMap projects={data.projects} apiKey={process.env.GOOGLE_MAPS_BROWSER_KEY ?? ""} mapId={process.env.GOOGLE_MAPS_MAP_ID || "DEMO_MAP_ID"}/>
    <div style={{marginTop: 18}}>
      <Callout tone="info" icon={Info}>O risco é um sinal das previsões (chance de cumprir o prazo e custo final estimado contra o orçamento), não uma
        conclusão. Mapas e imagens: Google Maps Platform; coordenadas obtidas do Google são renovadas a cada 30 dias, conforme os termos do serviço.</Callout>
    </div>
  </>;
}
