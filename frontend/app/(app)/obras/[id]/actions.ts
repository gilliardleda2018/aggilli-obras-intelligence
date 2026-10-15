"use server";
import {revalidatePath} from "next/cache";
import {accessToken} from "../../../../lib/session";

const API = process.env.API_BASE_URL || "http://localhost:8000";
type State = {ok: boolean; message: string};
const STATUSES = ["PLANNED", "IN_PROGRESS", "PAUSED", "DONE", "COST_POOL"];

function text(form: FormData, name: string, max: number): string | null {
  const value = String(form.get(name) ?? "").trim();
  return value ? value.slice(0, max) : null;
}

function decimal(form: FormData, name: string): string | null | undefined {
  const raw = String(form.get(name) ?? "").trim().replace(",", ".");
  if (!raw) return null;
  return /^-?\d+(\.\d+)?$/.test(raw) ? raw : undefined;
}

export async function updateProject(projectId: string, _prev: State, form: FormData): Promise<State> {
  const token = await accessToken();
  if (!token) return {ok: false, message: "Sessão expirada. Entre novamente."};
  const status = String(form.get("status") ?? "");
  const budget = decimal(form, "budget");
  if (!STATUSES.includes(status) || budget === undefined)
    return {ok: false, message: "Confira situação e orçamento (use ponto ou vírgula decimal)."};
  const date = (name: string) => {
    const value = String(form.get(name) ?? "");
    return /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : null;
  };
  const body = {
    municipality: text(form, "municipality", 120), address: text(form, "address", 300), responsible: text(form, "responsible", 200),
    cost_center: text(form, "cost_center", 60), status, budget, start_date: date("start_date"), end_date: date("end_date"),
  };
  try {
    const response = await fetch(API + "/api/v1/projects/" + encodeURIComponent(projectId), {
      method: "PATCH", headers: {Authorization: "Bearer " + token, "Content-Type": "application/json"}, body: JSON.stringify(body), cache: "no-store",
    });
    if (!response.ok) {
      return {ok: false, message: response.status === 404 ? "Acesso negado ou obra não encontrada."
        : response.status === 422 ? "Dados inválidos: confira as datas (término após o início)." : "Não foi possível salvar (" + response.status + ")."};
    }
  } catch {
    return {ok: false, message: "Não foi possível conectar à API."};
  }
  revalidatePath("/obras/" + projectId);
  return {ok: true, message: "Dados da obra atualizados."};
}
