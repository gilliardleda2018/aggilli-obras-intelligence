"use server";
import {revalidatePath} from "next/cache";
import {cookies} from "next/headers";
import {accessToken, sealSession} from "./session";
import type {LicenseStatus, OrgUser} from "./api";

const API = process.env.API_BASE_URL || "http://localhost:8000";
type Fail = {ok: false; message: string};

async function call<T>(method: string, path: string, body?: unknown): Promise<{ok: true; data: T} | Fail> {
  const token = await accessToken();
  if (!token) return {ok: false, message: "Sessão expirada. Entre novamente."};
  try {
    const response = await fetch(API + "/api/v1" + path, {method, cache: "no-store",
      headers: {Authorization: "Bearer " + token, "Content-Type": "application/json"}, body: body ? JSON.stringify(body) : undefined});
    const data = await response.json().catch(() => ({}));
    if (response.ok) return {ok: true, data: data as T};
    const detail = typeof data.detail === "string" ? data.detail : null;
    return {ok: false, message: detail ?? (response.status === 404 ? "Sem permissão." : "Erro " + response.status)};
  } catch {
    return {ok: false, message: "API indisponível."};
  }
}

const valid = (id: string) => /^[a-f0-9-]{36}$/i.test(id);

export async function changePassword(current: string, next: string): Promise<{ok: true} | Fail> {
  if (next.length < 10 || !/[A-Za-z]/.test(next) || !/\d/.test(next))
    return {ok: false, message: "A nova senha precisa ter pelo menos 10 caracteres, com letras e números."};
  const result = await call<{access_token: string; expires_in: number}>("POST", "/me/password", {current_password: current, new_password: next});
  if (!result.ok) return result;
  const key = process.env.SESSION_ENCRYPTION_KEY!;
  (await cookies()).set("obras_session", sealSession(result.data.access_token, key), {httpOnly: true,
    secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: result.data.expires_in});
  return {ok: true};
}

export async function addUser(orgId: string, input: {email: string; name: string; role: string}) {
  if (!valid(orgId)) return {ok: false, message: "Empresa inválida."} as Fail;
  const result = await call<OrgUser>("POST", "/organizations/" + orgId + "/users",
    {email: input.email.trim(), name: input.name.trim(), role: input.role});
  if (result.ok) revalidatePath("/usuarios");
  return result;
}

export async function changeUser(orgId: string, userId: string, change: {role?: string; active?: boolean}) {
  if (!valid(orgId) || !valid(userId)) return {ok: false, message: "Usuário inválido."} as Fail;
  const result = await call<OrgUser>("PATCH", "/organizations/" + orgId + "/users/" + userId, change);
  if (result.ok) revalidatePath("/usuarios");
  return result;
}

export async function resetPassword(orgId: string, userId: string) {
  if (!valid(orgId) || !valid(userId)) return {ok: false, message: "Usuário inválido."} as Fail;
  return call<OrgUser>("POST", "/organizations/" + orgId + "/users/" + userId + "/reset-password");
}

export async function activateLicense(code: string) {
  const result = await call<LicenseStatus>("POST", "/license/activate", {code: code.trim().slice(0, 4000)});
  if (result.ok) revalidatePath("/", "layout");
  return result;
}
