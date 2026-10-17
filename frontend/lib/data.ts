import {accessToken} from "./session";
import {sum} from "./portfolio";

/**
 * Single data source for the app pages: everything comes from the API (PostgreSQL), scoped to the session.
 * Without a session, or when the API fails, the dataset is empty — never the reference import (real FOPAG data),
 * which would otherwise reach anonymous visitors (and other organizations) inside the page payload.
 */
export type Source = "api" | "unavailable";

export type ProjectRow = {
  key: string; name: string; href: string; status: string; municipality: string | null;
  weekly: number; paid: number; open: number; flagged: number; activity: string | null;
  /** advanceValued: advances of contracts that have a total (used for the advance ratio). */
  contracts: {count: number; total: number; advance: number; balance: number; advanceValued: number};
  physical: null | {progress: number; planningComplete: boolean; services: number};
  budget: number | null; latitude: number | null; longitude: number | null;
};
export type ScheduleRow = {
  key: string; supplier: string; project: string; projectHref: string; work: string; category: string;
  notes: string | null; amount: number; status: string; date: string;
};
export type ContractRow = {contractor: string; project: string; projectHref: string; total: number | null; advance: number | null; balance: number | null};
export type PayableRow = {supplier: string; project: string; description: string; amount: number; scheduled: number; paid: number; outstanding: number; notes: string | null};
export type Dataset = {
  source: Source; sourceLabel: string; weekLabel: string; error?: string;
  projects: ProjectRow[]; schedule: ScheduleRow[]; contracts: ContractRow[]; payables: PayableRow[];
};

export const CATEGORY_LABEL: Record<string, string> = {
  LABOR: "Mão de obra", MATERIAL: "Material", SERVICE: "Serviço", FUEL: "Combustível", EQUIPMENT: "Equipamento", OTHER: "Outros",
};
const API = process.env.API_BASE_URL || "http://localhost:8000";
const n = (value: string | number | null | undefined) => (value === null || value === undefined ? 0 : Number(value));
const nn = (value: string | number | null | undefined) => (value === null || value === undefined ? null : Number(value));
const brDate = (iso: string) => iso.split("-").reverse().join("/");

export async function hasSession(): Promise<boolean> {
  return Boolean(await accessToken());
}

export async function getDataset(): Promise<Dataset> {
  const token = await accessToken();
  if (!token) return unavailable("Entre no sistema para ver os dados da sua organização.");
  const get = async <T>(path: string): Promise<T> => {
    const response = await fetch(API + "/api/v1" + path, {headers: {Authorization: "Bearer " + token}, cache: "no-store"});
    if (!response.ok) throw new Error(String(response.status));
    return response.json() as Promise<T>;
  };
  try {
    const [portfolio, schedule, contracts, payables] = await Promise.all([
      get<ApiPortfolio>("/portfolio"), get<ApiSchedule>("/schedule"), get<ApiContract[]>("/contracts"), get<ApiPayable[]>("/payables"),
    ]);
    const hrefById = Object.fromEntries(portfolio.projects.map(p => [p.id, "/obras/" + p.id]));
    return {
      source: "api",
      sourceLabel: "Banco de dados",
      weekLabel: schedule.start ? `Semana ${brDate(schedule.start)} a ${brDate(schedule.end!)}` : "Sem pagamentos programados",
      projects: portfolio.projects.map(p => ({
        key: p.id, name: p.name, href: hrefById[p.id], status: p.status, municipality: p.municipality,
        weekly: sum(schedule.items.filter(item => item.project_id === p.id).map(item => n(item.amount))),
        paid: n(p.paid_total), open: n(p.open_total), flagged: p.flagged_expenses,
        activity: p.latest_report?.summary.replace(/^Relato do contratante: /, "") ?? null,
        contracts: {count: p.contracts.count, total: n(p.contracts.total), advance: n(p.contracts.reported_advance),
          balance: n(p.contracts.reported_balance), advanceValued: n(p.contracts.advance_on_valued)},
        physical: p.physical && {progress: p.physical.progress, planningComplete: p.physical.planning_complete, services: p.physical.services},
        budget: nn(p.budget), latitude: p.latitude, longitude: p.longitude,
      })),
      schedule: schedule.items.map(item => ({
        key: item.payment_id, supplier: item.supplier, project: item.project, projectHref: hrefById[item.project_id],
        work: item.description, category: CATEGORY_LABEL[item.category] ?? item.category, notes: item.notes,
        amount: n(item.amount), status: item.status, date: item.scheduled_date,
      })),
      contracts: contracts.map(c => ({contractor: c.contractor, project: c.project, projectHref: hrefById[c.project_id],
        total: nn(c.total), advance: nn(c.reported_advance), balance: nn(c.reported_balance)})),
      payables: payables.map(p => ({supplier: p.supplier, project: p.project, description: p.description, amount: n(p.amount),
        scheduled: n(p.scheduled), paid: n(p.paid), outstanding: n(p.outstanding), notes: p.notes})),
    };
  } catch (error) {
    return unavailable("Não foi possível carregar os dados do banco (" + String(error) + "). Tente novamente.");
  }
}

function unavailable(error: string): Dataset {
  return {source: "unavailable", sourceLabel: "Dados indisponíveis", weekLabel: "Sem dados", error,
    projects: [], schedule: [], contracts: [], payables: []};
}

export function summarize(data: Dataset) {
  const weekly = sum(data.schedule.map(row => row.amount));
  const labor = sum(data.schedule.filter(row => row.category === "Mão de obra").map(row => row.amount));
  const works = data.projects.filter(p => p.status !== "COST_POOL");
  const contractTotal = sum(data.contracts.map(c => c.total ?? 0));
  const contractAdvance = sum(data.contracts.map(c => c.advance ?? 0));
  const contractAdvanceValued = sum(data.contracts.filter(c => c.total).map(c => c.advance ?? 0));
  return {
    weekly, labor, other: weekly - labor, items: data.schedule.length,
    laborItems: data.schedule.filter(row => row.category === "Mão de obra").length,
    paid: sum(data.schedule.filter(row => row.status === "PAID").map(row => row.amount)),
    flagged: data.schedule.filter(row => row.notes).length,
    contractTotal, contractAdvance, contractAdvanceValued, contractBalance: sum(data.contracts.map(c => c.balance ?? 0)), contractCount: data.contracts.length,
    open: sum(data.payables.map(p => p.outstanding)),
    debt: sum(data.payables.filter(p => p.description.startsWith("Saldo devedor")).map(p => p.outstanding)),
    debtCount: data.payables.filter(p => p.description.startsWith("Saldo devedor")).length,
    projects: works.length, measured: works.filter(p => p.physical).length,
  };
}

type ApiPortfolio = {projects: {
  id: string; name: string; status: string; municipality: string | null; budget: string | null; latitude: number | null; longitude: number | null;
  paid_total: string; open_total: string; flagged_expenses: number; latest_report: {date: string; summary: string} | null;
  contracts: {count: number; total: string; reported_advance: string; reported_balance: string; advance_on_valued: string};
  physical: null | {progress: number; planning_complete: boolean; services: number};
}[]};
type ApiSchedule = {start: string | null; end: string | null; items: {
  payment_id: string; project_id: string; project: string; supplier: string; description: string; category: string;
  notes: string | null; amount: string; scheduled_date: string; status: string;
}[]};
type ApiContract = {project_id: string; project: string; contractor: string; total: string | null; reported_advance: string | null; reported_balance: string | null};
type ApiPayable = {project: string; supplier: string; description: string; notes: string | null; amount: string; scheduled: string; paid: string; outstanding: string};
