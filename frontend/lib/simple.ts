import type {Alert, PortfolioIntelligence} from "./api";
import type {ProjectRow} from "./data";

/**
 * "Modo simples": the portfolio translated into a traffic light and one plain sentence per project, for owners
 * who do not read dashboards. Nothing is invented: a project without measurements is "sem medição", never green.
 */
export type Light = "red" | "yellow" | "green" | "gray";
export type SimpleProject = {id: string; name: string; href: string; light: Light; sentence: string; progress: number | null; measured: boolean};

const ORDER: Record<Light, number> = {red: 0, yellow: 1, green: 2, gray: 3};
const plural = (n: number, one: string, many: string) => n + " " + (n === 1 ? one : many);

export function simpleProjects(projects: ProjectRow[], intel: PortfolioIntelligence | null, alerts: Alert[]): SimpleProject[] {
  const open = alerts.filter(alert => !alert.review);
  return projects.filter(p => p.status !== "COST_POOL").map((project): SimpleProject => {
    const own = open.filter(alert => alert.project_id === project.key);
    const forecast = intel?.projects.find(p => p.id === project.key);
    const measured = forecast?.schedule.status === "ok" || forecast?.schedule.status === "concluida";
    const progress = measured ? Math.round(forecast!.schedule.current_progress) : project.physical ? Math.round(project.physical.progress) : null;
    const base = {id: project.key, name: project.name, href: project.href, progress, measured: progress !== null};

    const problems: string[] = [];
    if (own.some(a => a.type === "risco_atraso")) {
      const days = forecast?.schedule.delay_days_p50;
      problems.push(days && days > 0 ? "Pode atrasar uns " + plural(days, "dia", "dias") : "Pode atrasar");
    }
    if (own.some(a => a.type === "risco_estouro")) problems.push("pode gastar mais que o orçamento");
    if (problems.length) return {...base, light: "red", sentence: capitalize(problems.join(" e ")) + "."};

    const unconfirmed = own.filter(a => a.type === "pagamento_vencido").reduce((n, a) => n + Math.max(1, a.evidence.length), 0);
    if (unconfirmed) return {...base, light: "yellow", sentence: "Tem " + plural(unconfirmed, "pagamento", "pagamentos") + " para confirmar."};
    if (own.some(a => a.severity !== "low")) return {...base, light: "yellow", sentence: own.find(a => a.severity !== "low")!.title + "."};

    if (measured) return {...base, light: "green",
      sentence: forecast!.schedule.status === "concluida" ? "Obra concluída." : "Tudo certo. " + progress + "% pronta."};
    return {...base, light: "gray", sentence: "Ainda não foi medida. O sistema não sabe se está no prazo."};
  }).sort((a, b) => ORDER[a.light] - ORDER[b.light] || a.name.localeCompare(b.name, "pt-BR"));
}

/** The one sentence at the top: what the owner would hear from a foreman on the phone. */
export function headline(list: SimpleProject[]): {text: string; tone: Light; note: string | null} {
  const count = (light: Light) => list.filter(p => p.light === light).length;
  const [red, yellow] = [count("red"), count("yellow")];
  const unmeasured = list.filter(p => !p.measured).length;
  const note = unmeasured ? plural(unmeasured, "obra ainda não foi medida", "obras ainda não foram medidas") +
    ". Depois da medição, o sistema avisa se estão no prazo." : null;
  if (red) return {tone: "red", note, text: red === 1 ? "Uma obra precisa da sua atenção agora." : red + " obras precisam da sua atenção agora."};
  if (yellow) return {tone: "yellow", note, text: "Nada grave. " + (yellow === 1 ? "Uma obra tem" : yellow + " obras têm") + " pagamentos para confirmar."};
  if (!list.length) return {tone: "gray", note: null, text: "Nenhuma obra cadastrada ainda."};
  return {tone: "green", note, text: "Está tudo em ordem nas suas obras."};
}

export function greeting(now = new Date()): string {
  const hour = Number(now.toLocaleString("en-US", {hour: "numeric", hourCycle: "h23", timeZone: "America/Fortaleza"}));
  return hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";
}

/** "R$ 84 mil", "R$ 1,2 milhão": amounts the way people say them. */
export function spokenMoney(value: number): string {
  if (value >= 1_000_000) return "R$ " + (value / 1_000_000).toLocaleString("pt-BR", {maximumFractionDigits: 1}) + (value < 2_000_000 ? " milhão" : " milhões");
  if (value >= 1_000) return "R$ " + Math.round(value / 1_000).toLocaleString("pt-BR") + " mil";
  return value.toLocaleString("pt-BR", {style: "currency", currency: "BRL", maximumFractionDigits: 0});
}

const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
