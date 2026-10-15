"use server";
import {revalidatePath} from "next/cache";
import {accessToken} from "./session";

const API = process.env.API_BASE_URL || "http://localhost:8000";
type Result = {ok: true} | {ok: false; message: string; duplicate?: boolean};

async function post(path: string, body?: unknown): Promise<{status: number; detail?: string}> {
  const token = await accessToken();
  if (!token) return {status: 401};
  try {
    const response = await fetch(API + "/api/v1" + path, {method: "POST", cache: "no-store",
      headers: {Authorization: "Bearer " + token, "Content-Type": "application/json"}, body: body ? JSON.stringify(body) : undefined});
    const detail = response.ok ? undefined : (await response.json().catch(() => ({}))).detail;
    return {status: response.status, detail: typeof detail === "string" ? detail : undefined};
  } catch {
    return {status: 502};
  }
}

const valid = (id: string) => /^[a-f0-9-]{36}$/i.test(id);

export async function confirmDocument(id: string, input: {
  project_id: string; kind: string; supplier: string; description: string; amount: string; expense_date: string | null;
  category: string; notes: string | null; allow_duplicate: boolean;
}): Promise<Result> {
  if (!valid(id) || !valid(input.project_id)) return {ok: false, message: "Escolha a obra."};
  const amount = input.amount.replace(/\./g, "").replace(",", ".").trim();
  if (!/^\d+(\.\d{1,2})?$/.test(amount) || Number(amount) <= 0) return {ok: false, message: "Valor inválido. Use, por exemplo, 1.250,90."};
  if (!input.supplier.trim() || !input.description.trim()) return {ok: false, message: "Informe fornecedor e descrição."};
  const {status, detail} = await post("/documents/" + id + "/confirm", {...input, amount, expense_date: input.expense_date || null,
    supplier: input.supplier.trim().slice(0, 200), description: input.description.trim().slice(0, 300), notes: input.notes?.trim().slice(0, 500) || null});
  if (status === 200) {
    revalidatePath("/documentos");
    revalidatePath("/obras/" + input.project_id);
    return {ok: true};
  }
  if (status === 409) return {ok: false, message: detail ?? "Documento já conferido.", duplicate: (detail ?? "").startsWith("Já existe gasto")};
  return {ok: false, message: status === 401 ? "Sessão expirada. Entre novamente." : status === 404 ? "Sem permissão nesta obra." :
    status === 422 ? (detail ?? "Dados inválidos.") : "Erro " + status};
}

export async function discardDocument(id: string): Promise<Result> {
  if (!valid(id)) return {ok: false, message: "Documento inválido."};
  const {status} = await post("/documents/" + id + "/discard");
  if (status === 200) { revalidatePath("/documentos"); return {ok: true}; }
  return {ok: false, message: status === 409 ? "Documento já conferido." : "Erro " + status};
}
