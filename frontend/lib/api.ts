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

export type PhotoPlace = "NA_OBRA" | "FORA_DA_OBRA" | "SEM_LOCALIZACAO" | "OBRA_SEM_LOCAL";
export type DiaryPhoto = {
  id: string; report_id: string | null; service_id: string | null; service: string | null; caption: string | null; url: string;
  width: number; height: number; size_bytes: number; sha256: string; taken_at: string | null; taken_at_source: "EXIF" | "DEVICE" | null;
  latitude: number | null; longitude: number | null; accuracy_m: number | null; location_source: "EXIF" | "DEVICE" | null;
  place: PhotoPlace; distance_m: number | null; recorded_by: string; created_at: string;
};
export type Diary = {
  project: {id: string; name: string; located: boolean}; services: {id: string; name: string}[];
  days: {date: string; reports: {id: string; weather: string; summary: string; recorded_by: string}[]; photos: DiaryPhoto[]}[];
};

export type DocKind = "NOTA_FISCAL" | "RECIBO" | "ORCAMENTO" | "COMPROVANTE" | "OUTRO";
export type FieldDoc = {
  id: string; status: "PENDING" | "CONFIRMED" | "DISCARDED"; kind: DocKind | null; kind_label: string | null; url: string;
  width: number; height: number; project_id: string | null; project: string | null;
  suggested_project_id: string | null; suggested_project: string | null; suggestion_reason: string | null;
  latitude: number | null; longitude: number | null; location_source: "EXIF" | "DEVICE" | null; access_key: string | null;
  nfe: {access_key: string; uf: string; year_month: string; cnpj: string; model: string; series: string; number: string} | null;
  engine: string | null; read_error: string | null; problems: string[];
  draft: {supplier: string; supplier_cnpj: string | null; description: string; amount: string | null; expense_date: string | null;
    document_number: string | null; category: string | null; category_reason: string | null;
    items: {description: string; quantity: number | null; unit: string | null; total: number | null}[];
    site_reference: string | null; confidence: "high" | "medium" | "low" | null; issues: string[]};
  expense_id: string | null; recorded_by: string; created_at: string; taken_at: string | null; confirmed_by: string | null;
};

export type LicenseInfo = {enforced: boolean; state: "missing" | "active" | "expiring" | "grace" | "blocked"; days_left: number | null;
  expires_at: string | null; grace_ends: string | null};
export type Me = {id: string; email: string | null; name: string; must_change_password: boolean; local: boolean;
  organizations: {id: string; name: string; role: string}[]; license: LicenseInfo};
export type OrgUser = {membership_id: string; user_id: string; role: string; email: string | null; name: string; active: boolean;
  must_change_password: boolean; locked: boolean; last_login_at: string | null; local: boolean; temporary_password?: string | null};
export type LicenseStatus = LicenseInfo & {configured: boolean; holder: string | null; email: string | null; last_error: string | null;
  can_manage: boolean};


export type EngineeringFinding = {
  code: string; severity: "high" | "warning" | "info"; message: string;
  recommended_action: string; evidence: Record<string, unknown>;
};
export type EngineeringAdvice = {
  agent: "engenheiro-ia"; version: string; mode: "advisory";
  project_id: string; evaluated_on: string;
  findings: EngineeringFinding[]; writes_performed: false;
};


export type FinancialFinding = {
  code: string; severity: "high" | "warning" | "info"; project_id: string;
  message: string; recommended_action: string; evidence: Record<string, unknown>;
};
export type FinancialDiagnosis = {
  agent: "financeiro-ia"; version: string; mode: "advisory";
  projects: number; findings: FinancialFinding[]; writes_performed: false;
};


export type DocumentAuditFinding = {
  code: string; severity: "warning" | "info"; message: string;
  recommended_action: string; evidence: Record<string, unknown>;
};
export type DocumentAuditDiagnosis = {
  agent: "auditor-documental-ia"; version: string; mode: "advisory";
  documents: {document_id: string; status: string; source_sha256: string; findings: DocumentAuditFinding[]}[];
  writes_performed: false;
};
