import { cookies } from "next/headers";
import { createDecipheriv } from "node:crypto";

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
