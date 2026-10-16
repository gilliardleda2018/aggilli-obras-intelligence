"use server";
import {revalidatePath} from "next/cache";
import {accessToken} from "./session";

const API = process.env.API_BASE_URL || "http://localhost:8000";

export type ImportRow = {
  line: number; project: string | null; project_id: string | null; project_text: string; project_score: number | null; date: string | null;
  supplier?: string; description?: string; amount?: string | null; category?: string; paid?: boolean; notes?: string | null;
  classification?: {category: string; confidence: number; method: string; reason: string};
  service?: string; service_id?: string | null; quantity?: string | null; unit?: string | null; issues: string[]; ok: boolean; duplicate?: boolean;
};
export type Preview = {
  id: string; filename: string; rows: ImportRow[];
  summary: {kind: "expenses" | "measurements"; columns: Record<string, string>; rows: number; valid: number; with_issues: number; total: string | null;
    projects: string[]; classifier: {trained_on: number; method: string}};
};
export type PreviewState = {ok: boolean; message: string; preview?: Preview; committed?: {created: number; skipped: number; kind: string}};

export async function uploadSpreadsheet(_prev: PreviewState, form: FormData): Promise<PreviewState> {
  const token = await accessToken();
  if (!token) return {ok: false, message: "Sessão expirada. Entre novamente."};
  const file = form.get("file");
  if (!(file instanceof File) || !file.size) return {ok: false, message: "Escolha uma planilha .xlsx ou .csv."};
  if (file.size > 5 * 1024 * 1024) return {ok: false, message: "Arquivo acima de 5 MB."};
  const body = new FormData();
  body.append("file", file, file.name);
  const organization = String(form.get("organization_id") ?? "");
  if (organization) body.append("organization_id", organization);
  const project = String(form.get("default_project_id") ?? "");
  if (/^[a-f0-9-]{36}$/i.test(project)) body.append("default_project_id", project);
  try {
    const response = await fetch(API + "/api/v1/imports/preview", {method: "POST", headers: {Authorization: "Bearer " + token}, body, cache: "no-store"});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) return {ok: false, message: typeof data.detail === "string" ? data.detail : "Não foi possível ler a planilha (" + response.status + ")."};
    return {ok: true, message: "", preview: data as Preview};
  } catch {
    return {ok: false, message: "Não foi possível conectar à API."};
  }
}

export async function commitImport(_prev: PreviewState, form: FormData): Promise<PreviewState> {
  const token = await accessToken();
  if (!token) return {ok: false, message: "Sessão expirada. Entre novamente."};
  const id = String(form.get("batch_id") ?? "");
  if (!/^[a-f0-9-]{36}$/i.test(id)) return {ok: false, message: "Importação inválida."};
  const overrides: Record<string, {category?: string; project_id?: string}> = {};
  for (const [key, value] of form.entries()) {
    const match = /^(category|project)_(\d+)$/.exec(key);
    if (!match || !value) continue;
    overrides[match[2]] = {...overrides[match[2]], [match[1] === "category" ? "category" : "project_id"]: String(value)};
  }
  try {
    const response = await fetch(API + "/api/v1/imports/" + id + "/commit", {
      method: "POST", headers: {Authorization: "Bearer " + token, "Content-Type": "application/json"}, body: JSON.stringify({overrides}), cache: "no-store",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) return {ok: false, message: response.status === 409 ? "Esta planilha já foi confirmada." : "Não foi possível importar (" + response.status + ")."};
    revalidatePath("/", "layout");
    return {ok: true, message: "", committed: data};
  } catch {
    return {ok: false, message: "Não foi possível conectar à API."};
  }
}
