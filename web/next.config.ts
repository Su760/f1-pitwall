import type { NextConfig } from "next";

const apiUrl = (process.env.PITWALL_API_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

const config: NextConfig = {
  poweredByHeader: false,
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${apiUrl}/api/v1/:path*` },
    ];
  },
};

export default config;
