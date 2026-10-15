"use server";
import {revalidatePath} from "next/cache";
import {accessToken} from "./session";

const API = process.env.API_BASE_URL || "http://localhost:8000";
export type ReviewState = {ok: boolean; message: string};

export async function reviewAlert(alertKey: string, _prev: ReviewState, form: FormData): Promise<ReviewState> {
  const token = await accessToken();
  if (!token) return {ok: false, message: "Sessão expirada."};
  const decision = String(form.get("decision") ?? "");
  if (!["CONFIRMED", "FALSE_ALARM", "RESOLVED"].includes(decision)) return {ok: false, message: "Decisão inválida."};
  const note = String(form.get("note") ?? "").trim().slice(0, 500);
  try {
    const response = await fetch(API + "/api/v1/alerts/" + alertKey + "/review", {
      method: "POST", headers: {Authorization: "Bearer " + token, "Content-Type": "application/json"},
      body: JSON.stringify({decision, note: note || null}), cache: "no-store"});
    if (!response.ok) return {ok: false, message: response.status === 404 ? "Sem permissão para revisar ou alerta já resolvido." : "Erro " + response.status};
  } catch {
    return {ok: false, message: "API indisponível."};
  }
  revalidatePath("/", "layout");
  return {ok: true, message: "Revisão registrada."};
}
