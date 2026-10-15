import { cookies } from "next/headers";
import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";

export async function accessToken():Promise<string|null>{
  const key=process.env.SESSION_ENCRYPTION_KEY;
  const value=(await cookies()).get("obras_session")?.value;
  if(!key||!/^[a-f0-9]{64}$/i.test(key)||!value)return null;
  try{
    const raw=Buffer.from(value,"base64url");
    const decipher=createDecipheriv("aes-256-gcm",Buffer.from(key,"hex"),raw.subarray(0,12));
    decipher.setAuthTag(raw.subarray(12,28));
    return Buffer.concat([decipher.update(raw.subarray(28)),decipher.final()]).toString("utf8");
  }catch{return null;}
}

/** Encrypt an access token into the HttpOnly session cookie value (AES-256-GCM). */
export function sealSession(token:string,key:string):string{
  const iv=randomBytes(12);
  const cipher=createCipheriv("aes-256-gcm",Buffer.from(key,"hex"),iv);
  const encrypted=Buffer.concat([cipher.update(token,"utf8"),cipher.final()]);
  return Buffer.concat([iv,cipher.getAuthTag(),encrypted]).toString("base64url");
}
