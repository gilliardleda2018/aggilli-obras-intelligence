"use server";
import {revalidatePath} from "next/cache";
import {accessToken} from "./session";

const API = process.env.API_BASE_URL || "http://localhost:8000";
export type ActionState = {ok: boolean; message: string};

async function call(method: "POST", path: string, body?: unknown): Promise<ActionState & {status?: number}> {
  const token = await accessToken();
  if (!token) return {ok: false, message: "Sessão expirada. Entre novamente."};
  try {
    const response = await fetch(API + "/api/v1" + path, {
      method, headers: {Authorization: "Bearer " + token, "Content-Type": "application/json"},
      body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store",
    });
    if (response.ok) return {ok: true, message: "Registrado.", status: response.status};
    const messages: Record<number, string> = {
      404: "Sem permissão para esta ação ou registro não encontrado.",
      409: "Conflito: a soma ultrapassaria o previsto (pesos ou quantidade) ou a medição já foi decidida.",
      422: "Dados inválidos: confira quantidade, data (não pode ser futura) e textos obrigatórios.",
    };
    return {ok: false, message: messages[response.status] ?? "Não foi possível concluir (" + response.status + ").", status: response.status};
  } catch {
    return {ok: false, message: "Não foi possível conectar à API."};
  }
}

function decimal(value: FormDataEntryValue | null): string | null {
  const raw = String(value ?? "").trim().replace(",", ".");
  return /^\d+(\.\d{1,4})?$/.test(raw) && Number(raw) > 0 ? raw : null;
}

function refresh(projectId: string) {
  revalidatePath("/obras/" + projectId + "/medicoes");
  revalidatePath("/obras/" + projectId);
  revalidatePath("/medicoes");
  revalidatePath("/");
}

export async function createService(projectId: string, _prev: ActionState, form: FormData): Promise<ActionState> {
  const name = String(form.get("name") ?? "").trim();
  const unit = String(form.get("unit") ?? "").trim();
  const planned = decimal(form.get("planned_quantity"));
  const weight = decimal(form.get("weight"));
  if (!name || !unit || !planned || !weight || Number(weight) > 100) return {ok: false, message: "Preencha serviço, unidade, quantidade e peso (0–100)."};
  const result = await call("POST", "/projects/" + encodeURIComponent(projectId) + "/services",
    {name: name.slice(0, 200), unit: unit.slice(0, 30), planned_quantity: planned, weight});
  if (result.ok) refresh(projectId);
  return result.ok ? {ok: true, message: "Serviço cadastrado."} : result;
}

export async function recordMeasurement(projectId: string, _prev: ActionState, form: FormData): Promise<ActionState> {
  const serviceId = String(form.get("service_id") ?? "");
  const quantity = decimal(form.get("quantity"));
  const measuredOn = String(form.get("measured_on") ?? "");
  const notes = String(form.get("notes") ?? "").trim();
  if (!/^[a-f0-9-]{36}$/i.test(serviceId) || !quantity) return {ok: false, message: "Selecione o serviço e informe uma quantidade positiva."};
  const result = await call("POST", "/services/" + serviceId + "/measurements",
    {quantity, measured_on: /^\d{4}-\d{2}-\d{2}$/.test(measuredOn) ? measuredOn : null, notes: notes ? notes.slice(0, 500) : null});
  if (result.ok) refresh(projectId);
  return result.ok ? {ok: true, message: "Medição registrada — aguardando aprovação."} : result;
}

export async function decideMeasurement(projectId: string, _prev: ActionState, form: FormData): Promise<ActionState> {
  const id = String(form.get("measurement_id") ?? "");
  const decision = String(form.get("decision") ?? "");
  const reason = String(form.get("reason") ?? "").trim();
  if (!/^[a-f0-9-]{36}$/i.test(id) || !["approve", "reject"].includes(decision)) return {ok: false, message: "Ação inválida."};
  if (decision === "reject" && reason.length < 5) return {ok: false, message: "Informe o motivo da recusa (mínimo 5 caracteres)."};
  const result = decision === "approve"
    ? await call("POST", "/measurements/" + id + "/approve")
    : await call("POST", "/measurements/" + id + "/reject", {reason: reason.slice(0, 500)});
  if (result.ok) refresh(projectId);
  return result.ok ? {ok: true, message: decision === "approve" ? "Medição aprovada." : "Medição recusada."} : result;
}
