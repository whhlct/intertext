import type { NextConfig } from "next";

const backendUrl = process.env.INTERTEXT_BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    // Next 16.3 defaults this experimental subprocess path on, but its detached
    // compiler process can close before captured --showConfig output is read.
    useTypeScriptCli: false,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${backendUrl}/health`,
      },
    ];
  },
};

export default nextConfig;
