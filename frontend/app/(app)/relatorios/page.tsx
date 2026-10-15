import Link from "next/link";
import {FileSpreadsheet, FileText, Info, Lock, LogIn, Printer, Sheet} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Badge, Callout, Card} from "../../../components/ui";
import {Probability, br} from "../../../components/forecast-ui";
import {apiGet, type PortfolioIntelligence} from "../../../lib/api";
import {money} from "../../../lib/portfolio";

export const dynamic = "force-dynamic";
const STATUS: Record<string, string> = {PLANNED: "Planejada", IN_PROGRESS: "Em execução", PAUSED: "Paralisada", DONE: "Concluída", COST_POOL: "A ratear"};

export default async function Relatorios() {
  const data = await apiGet<PortfolioIntelligence>("/intelligence/portfolio");
  if (!data) return <>
    <PageHead title="Relatórios" subtitle="Planilhas e relatórios gerados a partir dos dados lançados."/>
    <Callout tone="info" icon={Lock}>Entre para gerar relatórios. <a className="link" href="/login"><LogIn size={14}/> Entrar</a></Callout>
  </>;
  const projects = [...data.projects].sort((a, b) => a.name.localeCompare(b.name));
  return <>
    <PageHead eyebrow="Saídas" title="Relatórios"
              subtitle="Tudo é gerado na hora a partir do que foi lançado — despesas, pagamentos, medições, materiais, previsões e alertas."/>
    <div className="grid-main">
      <div className="stack">
        <Card title="Carteira completa" subtitle="Uma planilha com todas as obras que você pode ver"
              action={<a className="btn primary" href="/api/download/reports/portfolio.xlsx"><FileSpreadsheet/>Baixar Excel</a>}>
          <p className="hint" style={{margin: 0}}>Abas: Resumo (avanço, custo, pago, em aberto, término P10/P50/P90, probabilidade no prazo, custo final estimado),
            Despesas, Pagamentos, Contratos, Medições, Materiais, Alertas e Sobre (método e data de geração).</p>
        </Card>
        <Card flush title="Por obra" subtitle="Relatório para imprimir/PDF, planilha da obra e despesas em CSV">
          {projects.map(p => <div key={p.id} className="list-item">
            <div style={{flex: 1}}>
              <b>{p.name}</b> <Badge tone="neutral">{STATUS[p.status] ?? p.status}</Badge>
              <small>{p.status === "COST_POOL" ? "Centro de custo — sem previsão de término" :
                p.schedule.status === "ok" ? "Término provável " + br(p.schedule.finish_p50) + (p.cost.eac_p50 ? " · custo final ~" + money(p.cost.eac_p50) : "")
                  : "Avanço " + p.schedule.current_progress.toLocaleString("pt-BR") + "% · previsão aguardando dados"}</small>
            </div>
            {p.status !== "COST_POOL" && <Probability value={p.schedule.probability_on_time}/>}
            <div className="actions" style={{display: "flex", gap: 6, flexWrap: "wrap"}}>
              <Link className="btn" href={"/relatorios/obra/" + p.id}><Printer/>Relatório</Link>
              <a className="btn" href={"/api/download/projects/" + p.id + "/reports/obra.xlsx"}><Sheet/>Excel</a>
              <a className="btn" href={"/api/download/projects/" + p.id + "/reports/expenses.csv"}><FileText/>CSV</a>
            </div>
          </div>)}
          {!projects.length && <p className="empty">Nenhuma obra disponível.</p>}
        </Card>
      </div>
      <div className="stack">
        <Callout tone="info" icon={Info}>Previsões aparecem com faixa de incerteza (P10–P90) e o modelo usado. Pagamentos programados não são pagamentos
          confirmados, e saldos de contratos são os informados na fonte. Os relatórios respeitam as permissões de quem os gera.</Callout>
      </div>
    </div>
  </>;
}
