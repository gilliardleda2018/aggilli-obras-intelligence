import Link from "next/link";
import {AlertTriangle, Building2, ChevronRight, HandCoins, LayoutDashboard} from "lucide-react";
import {Callout} from "../../../components/ui";
import {getDataset, summarize} from "../../../lib/data";
import {apiGet, type AlertsResponse, type PortfolioIntelligence} from "../../../lib/api";
import {greeting, headline, simpleProjects, spokenMoney, type Light} from "../../../lib/simple";

export const dynamic = "force-dynamic";

const LIGHT_LABEL: Record<Light, string> = {red: "Precisa agir", yellow: "Fique de olho", green: "Tudo certo", gray: "Sem medição"};

export default async function SimpleMode() {
  const data = await getDataset();
  const [intel, alerts] = data.source === "api"
    ? await Promise.all([apiGet<PortfolioIntelligence>("/intelligence/portfolio"), apiGet<AlertsResponse>("/alerts")])
    : [null, null];
  const list = simpleProjects(data.projects, intel, alerts?.alerts ?? []);
  const head = headline(list);
  const attention = list.filter(p => p.light === "red" || p.light === "yellow").length;
  const week = summarize(data).weekly;

  return <div className="simple">
    {data.error && <Callout icon={AlertTriangle}>{data.error}</Callout>}
    <p className="simple-hello">{greeting()}</p>
    <h1 className={"simple-headline tone-" + head.tone}>{head.text}</h1>
    {head.note && <p className="simple-note">{head.note}</p>}

    <div className="simple-cards">
      <div className="simple-card">
        <HandCoins aria-hidden/><span>Vai pagar esta semana</span><b>{spokenMoney(week)}</b>
      </div>
      <div className={"simple-card" + (attention ? " warn" : "")}>
        <AlertTriangle aria-hidden/><span>Obras pedindo atenção</span><b>{attention}</b>
      </div>
      <div className="simple-card">
        <Building2 aria-hidden/><span>Obras em andamento</span><b>{list.length}</b>
      </div>
    </div>

    <h2 className="simple-title">Suas obras</h2>
    <div className="simple-list">
      {list.map(p => <Link key={p.id} href={p.href} className="simple-row">
        <span className={"light " + p.light} role="img" aria-label={LIGHT_LABEL[p.light]}/>
        <div><b>{p.name}</b><span>{p.sentence}</span></div>
        <ChevronRight aria-hidden/>
      </Link>)}
      {!list.length && <p className="empty">Nenhuma obra cadastrada.</p>}
    </div>

    <p className="simple-legend">
      {(["green", "yellow", "red", "gray"] as Light[]).map(light =>
        <span key={light}><i className={"light " + light}/>{LIGHT_LABEL[light]}</span>)}
    </p>
    <Link className="btn simple-full" href="/"><LayoutDashboard/>Ver painel completo</Link>
  </div>;
}
