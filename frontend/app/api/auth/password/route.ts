import {NextResponse} from "next/server";
import {cookies} from "next/headers";
import {sealSession} from "../../../../lib/session";

const API = process.env.API_BASE_URL || "http://localhost:8000";

// E-mail + password sign-in (as in MG Transportes): the API checks the password; the token goes only into the
// encrypted HttpOnly cookie, never to the page.
export async function POST(request: Request) {
  const key = process.env.SESSION_ENCRYPTION_KEY;
  if (!key || !/^[a-f0-9]{64}$/i.test(key)) return NextResponse.json({message: "Login indisponível neste ambiente."}, {status: 503});
  const body = await request.json().catch(() => ({}));
  const email = typeof body.email === "string" ? body.email.trim().slice(0, 254) : "";
  const password = typeof body.password === "string" ? body.password.slice(0, 200) : "";
  if (!email || !password) return NextResponse.json({message: "Informe e-mail e senha."}, {status: 422});
  try {
    const response = await fetch(API + "/api/v1/auth/login", {method: "POST", cache: "no-store", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({email, password, remember: body.remember === true})});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) return NextResponse.json({message: typeof data.detail === "string" ? data.detail : "Não foi possível entrar."},
      {status: response.status});
    (await cookies()).set("obras_session", sealSession(data.access_token, key), {httpOnly: true, secure: process.env.NODE_ENV === "production",
      sameSite: "lax", path: "/", maxAge: Number(data.expires_in) || 3600});
    return NextResponse.json({mustChange: Boolean(data.must_change_password)});
  } catch {
    return NextResponse.json({message: "API indisponível."}, {status: 502});
  }
}
