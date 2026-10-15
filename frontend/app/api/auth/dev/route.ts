import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { sealSession } from "../../../../lib/session";

/**
 * Development sign-in (no identity provider): stores DEV_ACCESS_TOKEN — minted by
 * backend/scripts/dev_identity.py — in the regular encrypted session cookie.
 * Disabled unless ALLOW_DEV_LOGIN=1 and the request targets localhost.
 */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  const token = process.env.DEV_ACCESS_TOKEN;
  const key = process.env.SESSION_ENCRYPTION_KEY;
  if (process.env.ALLOW_DEV_LOGIN !== "1" || !local || !token || !key || !/^[a-f0-9]{64}$/i.test(key))
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  (await cookies()).set("obras_session", sealSession(token, key), { httpOnly: true, secure: false, sameSite: "lax", path: "/", maxAge: 8 * 3600 });
  return NextResponse.redirect(new URL("/", request.url));
}
