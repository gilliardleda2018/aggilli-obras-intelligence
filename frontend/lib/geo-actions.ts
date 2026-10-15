"use server";
import {revalidatePath} from "next/cache";
import {accessToken} from "./session";
import type {GeoCandidate, GeoLocation} from "./api";

const API = process.env.API_BASE_URL || "http://localhost:8000";
const MESSAGES: Record<number, string> = {
  0: "API indisponível.", 401: "Sessão expirada.", 404: "Sem permissão para alterar esta obra.",
  422: "Dados inválidos: confira o endereço ou as coordenadas (devem estar no Brasil).", 429: "Cota do Google Maps excedida; tente mais tarde.",
  502: "O serviço de geocodificação do Google não respondeu.", 503: "Geocodificação ainda não configurada (chave de servidor do Google Maps).",
};

async function call<T>(method: string, path: string, body: unknown): Promise<{ok: true; data: T} | {ok: false; message: string}> {
  const token = await accessToken();
  if (!token) return {ok: false, message: MESSAGES[401]};
  try {
    const response = await fetch(API + "/api/v1" + path, {method, cache: "no-store", body: JSON.stringify(body),
      headers: {Authorization: "Bearer " + token, "Content-Type": "application/json"}});
    if (!response.ok) return {ok: false, message: MESSAGES[response.status] ?? "Erro " + response.status};
    return {ok: true, data: await response.json() as T};
  } catch {
    return {ok: false, message: MESSAGES[0]};
  }
}

const valid = (id: string) => /^[a-f0-9-]{36}$/i.test(id);

export async function geocodeAddress(projectId: string, address: string) {
  if (!valid(projectId)) return {ok: false as const, message: "Obra inválida."};
  return call<{query: string; candidates: GeoCandidate[]}>("POST", "/projects/" + projectId + "/geocode", {address: address.trim().slice(0, 300) || null});
}

export type LocationInput = {latitude: number | null; longitude: number | null; source: "GEOCODED" | "MAP" | "FIELD" | "MANUAL" | null;
  accuracy?: string | null; place_id?: string | null};

export async function saveLocation(projectId: string, input: LocationInput) {
  if (!valid(projectId)) return {ok: false as const, message: "Obra inválida."};
  const located = input.latitude !== null && input.longitude !== null && Number.isFinite(input.latitude) && Number.isFinite(input.longitude);
  const result = await call<{location: GeoLocation}>("PUT", "/projects/" + projectId + "/location", located
    ? {latitude: Number(input.latitude!.toFixed(6)), longitude: Number(input.longitude!.toFixed(6)), source: input.source,
       accuracy: input.accuracy ?? null, place_id: input.source === "GEOCODED" ? input.place_id ?? null : null}
    : {});
  if (result.ok) { revalidatePath("/obras/" + projectId); revalidatePath("/mapa"); }
  return result;
}
