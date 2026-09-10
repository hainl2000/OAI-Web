import type { NextConfig } from "next";

// Backend origin. Requests to /api/* are proxied server-side so the session
// cookie stays same-origin (HttpOnly, SameSite=Lax).
const apiUrl = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
  },
};

export default nextConfig;
