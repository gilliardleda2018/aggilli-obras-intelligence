import { NextResponse } from "next/server";
import { randomBytes, createHash } from "node:crypto";
import { cookies } from "next/headers";

export async function GET(request: Request) {
  const issuer = process.env.OIDC_ISSUER;
  const clientId = process.env.OIDC_CLIENT_ID;
  const redirectUri = process.env.OIDC_REDIRECT_URI;
  if (!issuer || !clientId || !redirectUri || !issuer.startsWith("https://"))
    return NextResponse.json({error:"OIDC not configured"},{status:503});
  const state = randomBytes(32).toString("base64url");
  const verifier = randomBytes(32).toString("base64url");
  const challenge = createHash("sha256").update(verifier).digest("base64url");
  const store = await cookies();
  const secure = process.env.NODE_ENV === "production";
  store.set("obras_oidc_state",state,{httpOnly:true,secure,sameSite:"lax",path:"/",maxAge:600});
  store.set("obras_oidc_verifier",verifier,{httpOnly:true,secure,sameSite:"lax",path:"/",maxAge:600});
  const url = new URL(issuer.replace(/\/$/,"")+"/authorize");
  url.searchParams.set("response_type","code");
  url.searchParams.set("client_id",clientId);
  url.searchParams.set("redirect_uri",redirectUri);
  url.searchParams.set("scope","openid profile email");
  url.searchParams.set("state",state);
  url.searchParams.set("code_challenge",challenge);
  url.searchParams.set("code_challenge_method","S256");
  return NextResponse.redirect(url);
}
