/** @type {import('next').NextConfig} */

// Same-origin rule (PRD E.3): the browser only ever calls /api/*; Next.js
// rewrites proxy to the FastAPI backend. Local dev falls back to :8000; on
// Vercel set BACKEND_ORIGIN to the Fly URL (e.g. https://<app>.fly.dev).
// NOTE: read at BUILD time — changing BACKEND_ORIGIN needs a redeploy.
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || "http://127.0.0.1:8000";

const nextConfig = {
  // SSE (/api/events) streams through this rewrite proxy. The backend pings
  // every 15s; Next's default proxyTimeout (30s of inactivity) would cut the
  // stream if a ping were ever missed — pin it high instead of relying on
  // that undocumented 15s < 30s coupling.
  experimental: {
    proxyTimeout: 300_000,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_ORIGIN}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
