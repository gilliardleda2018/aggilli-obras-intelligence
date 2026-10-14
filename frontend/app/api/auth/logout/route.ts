import { NextResponse } from "next/server";
import { cookies } from "next/headers";
export async function GET(request:Request){
  (await cookies()).delete("obras_session");
  return NextResponse.redirect(new URL("/",request.url));
}
