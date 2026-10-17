import {NextResponse, type NextRequest} from "next/server";

// Operational pages need a session. Checked here, before anything renders: a redirect in the (app) layout does not stop
// the page itself from rendering, so its data would still travel in the 307 response. The API validates the token itself.
export function middleware(request: NextRequest) {
  if (request.cookies.get("obras_session")?.value) return NextResponse.next();
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  // Everything except the login page, auth/proxy route handlers (they answer 401 or redirect themselves) and static files.
  matcher: ["/((?!login|api/|_next/|favicon\.ico|.*\.(?:webp|png|jpg|jpeg|svg|ico|css|js|txt|map)$).*)"],
};
