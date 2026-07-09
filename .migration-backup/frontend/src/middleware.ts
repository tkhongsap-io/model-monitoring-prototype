import { NextRequest, NextResponse } from "next/server";

// Confidentiality guardrail (README / AGENTS.md: CPG Confidential, keep private).
// Optional HTTP Basic Auth over the whole app. DISABLED unless BOTH env vars are
// set, so it never blocks the first deploy — set them in Vercel project settings
// to gate the public URL before sharing:
//   BASIC_AUTH_USER=<user>   BASIC_AUTH_PASS=<strong-pass>
//
// NOTE: this protects the Vercel frontend only. The Fly backend URL stays
// reachable directly; keep it unguessable and harden it before wide sharing
// (see docs/DEPLOY.md → "Hardening").

export const config = {
  // Everything except Next internals / static assets.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

export function middleware(req: NextRequest) {
  const user = process.env.BASIC_AUTH_USER;
  const pass = process.env.BASIC_AUTH_PASS;
  if (!user || !pass) return NextResponse.next(); // auth off unless both set

  const header = req.headers.get("authorization");
  if (header?.startsWith("Basic ")) {
    const decoded = atob(header.slice(6));
    const sep = decoded.indexOf(":");
    if (sep !== -1 && decoded.slice(0, sep) === user && decoded.slice(sep + 1) === pass) {
      return NextResponse.next();
    }
  }
  return new NextResponse("Authentication required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Control Tower", charset="UTF-8"' },
  });
}
