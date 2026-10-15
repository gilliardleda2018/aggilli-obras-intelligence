"use server";
import {revalidatePath} from "next/cache";
import {accessToken} from "./session";

const API = process.env.API_BASE_URL || "http://localhost:8000";

export async function createReport(projectId: string, input: {date: string; weather: string; summary: string}):
  Promise<{ok: true; id: string} | {ok: false; message: string}> {
  if (!/^[a-f0-9-]{36}$/i.test(projectId)) return {ok: false, message: "Obra inválida."};
  if (!/^\d{4}-\d{2}-\d{2}$/.test(input.date)) return {ok: false, message: "Data inválida."};
  const summary = input.summary.trim().slice(0, 5000);
  if (!summary) return {ok: false, message: "Conte o que foi feito no dia."};
  const token = await accessToken();
  if (!token) return {ok: false, message: "Sessão expirada. Entre novamente."};
  try {
    const response = await fetch(API + "/api/v1/projects/" + projectId + "/field-reports", {method: "POST", cache: "no-store",
      headers: {Authorization: "Bearer " + token, "Content-Type": "application/json"},
      body: JSON.stringify({report_date: input.date, weather: input.weather.slice(0, 100), summary})});
    if (!response.ok) return {ok: false, message: response.status === 404 ? "Sem permissão para lançar nesta obra." : "Erro " + response.status};
    return {ok: true, id: (await response.json()).id};
  } catch {
    return {ok: false, message: "API indisponível."};
  }
}

export async function refreshDiary(projectId: string) {
  if (/^[a-f0-9-]{36}$/i.test(projectId)) revalidatePath("/obras/" + projectId + "/diario");
}
