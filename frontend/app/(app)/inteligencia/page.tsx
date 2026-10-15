import Link from "next/link";
import {BrainCircuit, CalendarClock, ChevronRight, Lock, LogIn, TrendingUp, Wallet} from "lucide-react";
import {PageHead} from "../../../components/app-shell";
import {Badge, Callout, Card, Kpi, Meter} from "../../../components/ui";
import {CostSummary, Probability, ScheduleSummary, br, modelLabel} from "../../../components/forecast-ui";
import {apiGet, type PortfolioIntelligence} from "../../../lib/api";
import {compactMoney, money, pct, sum} from "../../../lib/portfolio";

export const dynamic = "force-dynamic";

export default async function Inteligencia() {
  const data = await apiGet<PortfolioIntelligence>("/intelligence/portfolio");
  if (!data) return <>
    <PageHead eyebrow="Inteligência" title="Previsões das obras" subtitle="Término provável, custo final e caixa, calculados a partir do que é lançado."/>
    <Callout tone="info" icon={Lock}>As previsões são calculadas sobre os dados do banco. <a className="link" href="/login"><LogIn size={14}/> Entrar</a></Callout>
  </>;
  const rank = (r: PortfolioIntelligence["projects"][number]) => r.schedule.status === "ok" ? (r.schedule.probability_on_time ?? 1) : r.cost.status === "ok" ? 2 : 3 + (100 - r.schedule.current_progress) / 1000;
  const rows = [...data.projects].sort((a, b) => rank(a) - rank(b));
  const forecasted = rows.filter(r => r.schedule.status === "ok");
  const late = forecasted.filter(r => (r.schedule.delay_days_p50 ?? 0) > 0);
  const costed = rows.filter(r => r.cost.status === "ok");
  const weeks = data.cash.filter((c): c is {week_start: string; scheduled: string} => "week_start" in c);
  const overdue = Number((data.cash.find(c => "overdue_scheduled" in c) as {overdue_scheduled: string} | undefined)?.overdue_scheduled ?? 0);
  const maxWeek = Math.max(1, ...weeks.map(w => Number(w.scheduled)));
  return <>
    <PageHead eyebrow="Inteligência" title="Previsões das obras"
              subtitle="Recalculadas automaticamente a cada medição aprovada e despesa lançada; cada previsão guarda modelo, versão e histórico."/>
    <div className="kpis">
      <Kpi label="Obras com previsão de término" value={forecasted.length + " de " + rows.length} note="as demais mostram o que falta lançar"
           icon={BrainCircuit}/>
      <Kpi label="Com atraso projetado" value={String(late.length)} note="previsão central após a data contratual" icon={CalendarClock}
           tone={late.length ? "danger" : "ok"}/>
      <Kpi label="Custo final estimado" value={costed.length ? compactMoney(sum(costed.map(r => r.cost.eac_p50!))) : "—"}
           note={costed.length + " obras com previsão de custo"} icon={TrendingUp} tone="info"/>
      <Kpi label="Caixa programado (8 semanas)" value={compactMoney(sum(weeks.map(w => Number(w.scheduled))))}
           note={overdue ? compactMoney(overdue) + " programados em semanas passadas e não pagos" : "pagamentos programados à frente"}
           icon={Wallet} tone="warn"/>
    </div>

    <Card flush title="Término e custo por obra" subtitle="Faixa P10–P90 da simulação; probabilidade ainda não calibrada com obras concluídas">
      <div className="intel-grid intel-head"><span>Obra</span><span>Término provável</span><span>Custo final estimado</span><span>No prazo</span><span/></div>
      {rows.map(row => <Link key={row.id} href={"/obras/" + row.id} className="intel-grid">
        <div>
          <b>{row.name}</b> {row.source?.startsWith("SINTÉTICO") && <Badge tone="warn">Sintético</Badge>}
          <div className="meter-label" style={{marginTop: 6}}><span>Avanço medido</span><span>{row.schedule.current_progress.toLocaleString("pt-BR")}%</span></div>
          <Meter value={row.schedule.current_progress} tone="var(--ok)"/>
        </div>
        <ScheduleSummary s={row.schedule}/>
        <CostSummary c={row.cost}/>
        <Probability value={row.schedule.probability_on_time}/>
        <ChevronRight className="chev" size={18}/>
      </Link>)}
      {!rows.length && <p className="empty">Nenhuma obra cadastrada.</p>}
    </Card>

    <div className="grid-2" style={{marginTop: 18}}>
      <Card title="Caixa das próximas semanas" subtitle="Pagamentos programados por semana (todas as obras)">
        <div className="bars">
          {weeks.map(w => <div key={w.week_start} className="bar-row">
            <span>{br(w.week_start)}</span><Meter value={pct(Number(w.scheduled), maxWeek)} tone="var(--warn)"/><b>{money(Number(w.scheduled))}</b>
          </div>)}
        </div>
      </Card>
      <Card title="Como as previsões são feitas" subtitle="Métodos reconhecidos de gestão de projetos">
        <ul className="missing" style={{display: "grid", gap: 8}}>
          <li><b>Término:</b> simulação de Monte Carlo (5.000 cenários) sobre a produtividade semanal medida, com peso maior para as semanas
            recentes; Earned Schedule (Lipke) mede o atraso em tempo. Modelo: {modelLabel("monte-carlo-produtividade", "1.0")}.</li>
          <li><b>Custo final:</b> Valor Agregado (PMI) — EV, CPI, SPI e três fórmulas de EAC; sem orçamento, custo por ponto de avanço
            medido com intervalo por reamostragem.</li>
          <li><b>Honestidade:</b> sem medições suficientes, a obra mostra o que falta lançar — nenhum número é inventado. Pagamentos não
            viram avanço físico.</li>
          <li><b>Aprendizado:</b> cada previsão fica guardada; com obras concluídas, a probabilidade passa a ser calibrada e modelos de
            aprendizado de máquina entre obras (ex.: gradient boosting) são comparados por validação temporal antes de serem promovidos.</li>
        </ul>
      </Card>
    </div>
  </>;
}
