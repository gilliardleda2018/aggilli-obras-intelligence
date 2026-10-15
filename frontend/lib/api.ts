import {accessToken} from "./session";

const API = process.env.API_BASE_URL || "http://localhost:8000";

/** Authenticated GET against the API; null when there is no session or the call fails. */
export async function apiGet<T>(path: string): Promise<T | null> {
  const token = await accessToken();
  if (!token) return null;
  try {
    const response = await fetch(API + "/api/v1" + path, {headers: {Authorization: "Bearer " + token}, cache: "no-store"});
    return response.ok ? ((await response.json()) as T) : null;
  } catch {
    return null;
  }
}

export type ServiceRow = {
  id: string; name: string; unit: string; planned_quantity: string; weight: string; approved_quantity: string;
  pending_quantity: string; remaining_quantity: string; progress: number;
};
export type MeasurementRow = {
  id: string; project_id: string; project: string; service_id: string; service: string; unit: string; quantity: string;
  status: "PENDING" | "APPROVED" | "REJECTED"; recorded_by: string; measured_on: string | null; notes: string | null;
  created_at: string; decided_by: string | null; decided_at: string | null; decision_reason: string | null;
};

export type ScheduleForecast = {
  status: "ok" | "dados_insuficientes" | "concluida" | "sem_produtividade"; missing?: string[] | null; model: string; version: string;
  current_progress: number; contract_end: string | null; finish_p10?: string; finish_p50?: string; finish_p90?: string;
  deterministic_finish?: string | null; probability_on_time?: number; delay_days_p50?: number;
  productivity?: {average_pp_per_week: number; recent_pp_per_week: number}; simulations?: number;
  earned_schedule?: {planned_progress_now: number; spi_t: number | null; ieac_finish: string | null; baseline: string};
  backtest?: {predicted_last_progress: number; actual_last_progress: number; intervals_used: number};
  critical_services?: {name: string; progress: number; weight: number}[]; factors?: string[];
};
export type CostForecast = {
  status: "ok" | "dados_insuficientes"; missing?: string[] | null; model: string; version: string; actual_cost: number;
  physical_progress: number; budget: number | null; earned_value?: number; planned_value?: number | null; cpi?: number; spi?: number | null;
  eac_p50?: number; eac_low?: number; eac_high?: number; vac?: number; cost_per_point?: number; methods?: Record<string, number>; factors?: string[];
};
export type ProjectIntelligence = {
  schedule: ScheduleForecast; cost: CostForecast;
  series: {progress: {date: string; progress: number}[]; cost: {date: string; cost: number}[]; baseline: {date: string; progress: number}[]};
  cash: ({week_start: string; scheduled: string} | {overdue_scheduled: string})[];
  history: {kind: string; model: string; version: string; status: string; created_at: string; summary: Record<string, number | string | null>}[];
};
export type PortfolioIntelligence = {
  projects: {id: string; name: string; status: string; source: string | null; schedule: ScheduleForecast; cost: CostForecast}[];
  cash: ({week_start: string; scheduled: string} | {overdue_scheduled: string})[];
};

export type Alert = {
  key: string; type: string; severity: "high" | "medium" | "low"; project_id: string; project: string; title: string; detail: string;
  evidence: {kind: string; id: string; label: string}[]; review: null | {decision: string; note: string | null; by: string; at: string};
};
export type AlertsResponse = {alerts: Alert[]; open: number; feedback: Record<string, {confirmed: number; false_alarm: number}>};
export type TrendWeek = {week_start: string; incurred: Record<string, string>; incurred_total: string; paid: string; scheduled: string; entries: number};

export type MaterialRow = {
  id: string; project_id: string; project?: string; name: string; unit: string; category: string | null; balance: string; min_stock: string | null;
  avg_cost: string | null; stock_value: string; purchased: string; consumed: string; consumed_value: string; daily_consumption_30d: string;
  coverage_days: number | null; planned_quantity: string | null; service_id: string | null; service: string | null; service_progress: number | null;
  expected_consumption: string | null; flags: string[];
};
export type MovementRow = {id: string; kind: "IN" | "OUT"; quantity: string; date: string; unit_cost: string | null; supplier: string | null;
  note: string | null; expense_id: string | null; recorded_by: string};

export type GeoLocation = {latitude: number | null; longitude: number | null; source: "GEOCODED" | "MAP" | "FIELD" | "MANUAL" | null;
  accuracy: string | null; place_id: string | null; confirmed_by: string | null; confirmed_at: string | null; refresh_due: boolean};
export type MapProject = {
  id: string; name: string; organization: string; status: string; municipality: string | null; address: string | null; responsible: string | null;
  source: string | null; progress: number | null; finish_p50: string | null; probability_on_time: number | null; eac_p50: number | null;
  budget: number | null; risk: {level: "alto" | "medio" | "baixo" | "sem_dados" | "concluida"; reasons: string[]}; location: GeoLocation;
};
export type GeoCandidate = {formatted_address: string; latitude: number; longitude: number; accuracy: string | null; place_id: string;
  municipality: string | null; state: string | null; types: string[]; warnings: string[]};
