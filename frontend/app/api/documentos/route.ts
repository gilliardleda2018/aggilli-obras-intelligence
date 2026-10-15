import {NextResponse} from "next/server";
import {accessToken} from "../../../lib/session";

const API = process.env.API_BASE_URL || "http://localhost:8000";
const FIELDS = ["project_id", "latitude", "longitude", "accuracy", "taken_at"];
const MESSAGES: Record<number, string> = {
  401: "Sessão expirada. Entre novamente.", 404: "Sem permissão para enviar documentos.", 409: "Este documento já foi enviado.",
  413: "Foto maior que 15 MB.", 415: "Arquivo não é uma foto (use JPEG, PNG ou WEBP).", 422: "Dados do documento inválidos.",
};

// Route handler (not a server action) so phone pictures are not cut by the server-action size limit; reading can take seconds.
export async function POST(request: Request) {
  const token = await accessToken();
  if (!token) return NextResponse.json({message: MESSAGES[401]}, {status: 401});
  const form = await request.formData();
  const file = form.get("file");
  if (!(file instanceof File) || !file.size) return NextResponse.json({message: "Escolha uma foto do documento."}, {status: 422});
  const body = new FormData();
  body.append("file", file, file.name || "documento.jpg");
  for (const field of FIELDS) {
    const value = form.get(field);
    if (typeof value === "string" && value.trim()) body.append(field, value.trim());
  }
  try {
    const response = await fetch(API + "/api/v1/documents", {method: "POST", body, cache: "no-store", headers: {Authorization: "Bearer " + token}});
    if (!response.ok) return NextResponse.json({message: MESSAGES[response.status] ?? "Erro " + response.status}, {status: response.status});
    return NextResponse.json(await response.json(), {status: 201});
  } catch {
    return NextResponse.json({message: "API indisponível."}, {status: 502});
  }
}
