import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { randomBytes, createCipheriv } from "node:crypto";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const store = await cookies();
  const state = store.get("obras_oidc_state")?.value;
  const verifier = store.get("obras_oidc_verifier")?.value;
  store.delete("obras_oidc_state");
  store.delete("obras_oidc_verifier");
  if (!state || !verifier || state !== url.searchParams.get("state") || !url.searchParams.get("code"))
    return NextResponse.json({error:"Invalid authentication response"},{status:401});
  const issuer=process.env.OIDC_ISSUER;
  const clientId=process.env.OIDC_CLIENT_ID;
  const redirectUri=process.env.OIDC_REDIRECT_URI;
  const secret=process.env.OIDC_CLIENT_SECRET;
  const key=process.env.SESSION_ENCRYPTION_KEY;
  if(!issuer||!clientId||!redirectUri||!secret||!key||!issuer.startsWith("https://")||!/^[a-f0-9]{64}$/i.test(key))
    return NextResponse.json({error:"Authentication not configured"},{status:503});
  const response=await fetch(issuer.replace(/\/$/,"")+"/token",{
    method:"POST",headers:{"content-type":"application/x-www-form-urlencoded"},
    body:new URLSearchParams({grant_type:"authorization_code",code:url.searchParams.get("code")!,
      redirect_uri:redirectUri,client_id:clientId,client_secret:secret,code_verifier:verifier}),
    cache:"no-store"
  });
  if(!response.ok)return NextResponse.json({error:"Token exchange failed"},{status:401});
  const data=await response.json();
  if(typeof data.access_token!=="string"||!data.access_token)
    return NextResponse.json({error:"Invalid token response"},{status:401});
  const iv=randomBytes(12);
  const cipher=createCipheriv("aes-256-gcm",Buffer.from(key,"hex"),iv);
  const encrypted=Buffer.concat([cipher.update(data.access_token,"utf8"),cipher.final()]);
  const value=Buffer.concat([iv,cipher.getAuthTag(),encrypted]).toString("base64url");
  store.set("obras_session",value,{httpOnly:true,secure:process.env.NODE_ENV==="production",
    sameSite:"lax",path:"/",maxAge:Math.min(Math.max(Number(data.expires_in)||300,1),3600)});
  return NextResponse.redirect(new URL("/obras",request.url));
}
