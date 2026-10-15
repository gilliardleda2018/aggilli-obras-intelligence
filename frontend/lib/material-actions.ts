"use server";
import {revalidatePath} from "next/cache";
import {accessToken} from "./session";

const API = process.env.API_BASE_URL || "http://localhost:8000";
export type MaterialState = {ok: boolean; message: string};

const decimal = (value: FormDataEntryValue | null) => {
  const raw = String(value ?? "").trim().replace(/\./g, (m, i, s) => (s.includes(",") ? "" : m)).replace(",", ".");
  return raw && /^\d+(\.\d+)?$/.test(raw) ? raw : null;
};

async function post(path: string, body: unknown, method = "POST"): Promise<{ok: boolean; status: number}> {
  const token = await accessToken();
  if (!token) return {ok: false, status: 401};
  try {
    const response = await fetch(API + "/api/v1" + path, {method, headers: {Authorization: "Bearer " + token, "Content-Type": "application/json"},
      body: JSON.stringify(body), cache: "no-store"});
    return {ok: response.ok, status: response.status};
  } catch {
    return {ok: false, status: 0};
  }
}

const MESSAGES: Record<number, string> = {
  0: "API indisponível.", 401: "Sessão expirada.", 404: "Sem permissão ou registro não encontrado.",
  409: "Saldo insuficiente para essa saída.", 422: "Dados inválidos: confira quantidade, data (não futura) e, para gerar despesa, custo e fornecedor.",
};

export async function createMaterial(projectId: string, _prev: MaterialState, form: FormData): Promise<MaterialState> {
  const name = String(form.get("name") ?? "").trim();
  const unit = String(form.get("unit") ?? "").trim();
  if (!name || !unit) return {ok: false, message: "Informe material e unidade."};
  const service = String(form.get("service_id") ?? "");
  const result = await post("/projects/" + encodeURIComponent(projectId) + "/materials", {
    name: name.slice(0, 200), unit: unit.slice(0, 30), category: String(form.get("category") ?? "").trim().slice(0, 60) || null,
    min_stock: decimal(form.get("min_stock")), planned_quantity: decimal(form.get("planned_quantity")),
    service_id: /^[a-f0-9-]{36}$/i.test(service) ? service : null});
  if (result.ok) revalidatePath("/obras/" + projectId + "/materiais");
  return result.ok ? {ok: true, message: "Material cadastrado."} : {ok: false, message: MESSAGES[result.status] ?? "Erro " + result.status};
}

export async function recordMovement(projectId: string, _prev: MaterialState, form: FormData): Promise<MaterialState> {
  const material = String(form.get("material_id") ?? "");
  const kind = String(form.get("kind") ?? "");
  const quantity = decimal(form.get("quantity"));
  if (!/^[a-f0-9-]{36}$/i.test(material) || !["IN", "OUT"].includes(kind) || !quantity) return {ok: false, message: "Escolha o material, o tipo e a quantidade."};
  const date = String(form.get("movement_date") ?? "");
  const result = await post("/materials/" + material + "/movements", {
    kind, quantity, movement_date: /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : null, unit_cost: kind === "IN" ? decimal(form.get("unit_cost")) : null,
    supplier: kind === "IN" ? String(form.get("supplier") ?? "").trim().slice(0, 200) || null : null,
    note: String(form.get("note") ?? "").trim().slice(0, 300) || null, create_expense: kind === "IN" && form.get("create_expense") === "on"});
  if (result.ok) { revalidatePath("/obras/" + projectId + "/materiais"); revalidatePath("/materiais"); }
  return result.ok ? {ok: true, message: kind === "IN" ? "Entrada registrada." : "Saída registrada."} : {ok: false, message: MESSAGES[result.status] ?? "Erro " + result.status};
}
