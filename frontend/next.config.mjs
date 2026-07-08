/** @type {import('next').NextConfig} */
const nextConfig = {
  // Same-origin rule (PRD E.3): the browser only ever calls /api/*;
  // Next.js rewrites proxy to the FastAPI backend on :8000.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
