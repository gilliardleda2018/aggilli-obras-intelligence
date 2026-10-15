import { NextResponse } from "next/server";
import { accessToken } from "../../../../lib/session";

const API = process.env.API_BASE_URL || "http://localhost:8000";
// Only report files can be downloaded through this proxy (the browser never sees the access token).
const ALLOWED = [
  /^reports\/portfolio\.xlsx$/,
  /^projects\/[a-f0-9-]{36}\/reports\/(obra\.xlsx|expenses\.csv|progress\.csv)$/,
];

export async function GET(_request: Request, { params }: { params: Promise<{ path: string[] }> }) {
  const path = (await params).path.join("/");
  if (!ALLOWED.some(pattern => pattern.test(path))) return NextResponse.json({ error: "Not found" }, { status: 404 });
  const token = await accessToken();
  if (!token) return NextResponse.redirect(new URL("/login", _request.url));
  const response = await fetch(API + "/api/v1/" + path, { headers: { Authorization: "Bearer " + token }, cache: "no-store" });
  if (!response.ok) return NextResponse.json({ error: "Unavailable" }, { status: response.status === 404 ? 404 : 502 });
  return new NextResponse(response.body, {
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "application/octet-stream",
      "Content-Disposition": response.headers.get("content-disposition") ?? "attachment",
      "Cache-Control": "no-store",
    },
  });
}
