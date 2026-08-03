import type { NextConfig } from "next";

import { buildAppRedirects } from "./src/lib/seo/legacy-redirects";

/** Local FastAPI target for same-origin `/api/*` rewrites (ngrok / single-tunnel). */
const apiProxyTarget = (process.env.API_PROXY_TARGET || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

const nextConfig: NextConfig = {
  output: "standalone",
  // Public / tunnel hosts (Next 16 blocks cross-origin dev assets by default)
  allowedDevOrigins: [
    "127.0.0.1",
    "localhost",
    "padeya.com",
    "www.padeya.com",
    "rat-meetings-parish-fair.trycloudflare.com",
    "*.trycloudflare.com",
    "mesic-lera-indigestive.ngrok-free.dev",
    "*.ngrok-free.dev",
    "*.ngrok-free.app",
    "*.ngrok.app",
    "*.ngrok.io",
  ],
  images: {
    // Official brand PNGs are served from /public/brand
    formats: ["image/avif", "image/webp"],
    // Trusted asset hosts only — no hostname "**" (SSRF-style risk).
    remotePatterns: [
      {
        protocol: "https",
        hostname: "media.padeya.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "padeya.com",
        pathname: "/media/**",
      },
      {
        protocol: "https",
        hostname: "www.padeya.com",
        pathname: "/media/**",
      },
      {
        protocol: "https",
        hostname: "padeyawebsite.onrender.com",
        pathname: "/media/**",
      },
      {
        protocol: "http",
        hostname: "127.0.0.1",
        port: "8000",
        pathname: "/media/**",
      },
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
        pathname: "/media/**",
      },
    ],
  },
  async rewrites() {
    // beforeFiles: proxy API before App Router resolves /api/* as a page 404.
    // Scope to /api/v1 so Next routes like /api/revalidate/* stay local.
    return {
      beforeFiles: [
        {
          source: "/api/v1/:path*",
          destination: `${apiProxyTarget}/api/v1/:path*`,
        },
        {
          source: "/media/:path*",
          destination: `${apiProxyTarget}/media/:path*`,
        },
      ],
    };
  },
  async redirects() {
    // Single source of truth: src/lib/seo/legacy-redirects.ts
    // www→apex + product aliases + WordPress membership migrations.
    // Do NOT add a catch-all 404 → / redirect here.
    return buildAppRedirects();
  },
};

export default nextConfig;
