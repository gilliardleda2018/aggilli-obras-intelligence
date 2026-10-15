import {NextResponse} from "next/server";
import {accessToken} from "../../../../lib/session";

const API = process.env.API_BASE_URL || "http://localhost:8000";

// Document pictures are private: this proxy adds the session token, which never reaches the page.
export async function GET(request: Request, {params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  if (!/^[a-f0-9-]{36}$/i.test(id)) return NextResponse.json({error: "Not found"}, {status: 404});
  const token = await accessToken();
  if (!token) return NextResponse.redirect(new URL("/login", request.url));
  const response = await fetch(API + "/api/v1/documents/" + id + "/file", {headers: {Authorization: "Bearer " + token}, cache: "no-store"});
  if (!response.ok) return NextResponse.json({error: "Unavailable"}, {status: response.status === 404 ? 404 : 502});
  return new NextResponse(response.body, {headers: {
    "Content-Type": response.headers.get("content-type") ?? "image/jpeg", "Cache-Control": "private, max-age=86400",
  }});
}
