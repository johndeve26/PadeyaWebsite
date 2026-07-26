import type { NextConfig } from "next";

/** Local FastAPI target for same-origin `/api/*` rewrites (ngrok / single-tunnel). */
const apiProxyTarget = (process.env.API_PROXY_TARGET || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

const nextConfig: NextConfig = {
  output: "standalone",
  // Public / tunnel hosts (Next 16 blocks cross-origin dev assets by default)
  allowedDevOrigins: [
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
    // Host Command Center stays canonical at `/host`.
    // Do not add `/dashboard/host` aliases in this phase (Option B rejected).
    return [
      // Apex canonical — www must not serve a separate indexable duplicate.
      {
        source: "/:path*",
        has: [{ type: "host", value: "www.padeya.com" }],
        destination: "https://padeya.com/:path*",
        permanent: true,
      },
      {
        source: "/",
        has: [{ type: "host", value: "www.padeya.com" }],
        destination: "https://padeya.com/",
        permanent: true,
      },
      {
        source: "/host/dashboard",
        destination: "/host",
        permanent: true,
      },
      {
        source: "/host/dashboard/:path*",
        destination: "/host",
        permanent: true,
      },
      {
        source: "/host/events/:id/merch",
        destination: "/host/events/:id/merchandise",
        permanent: true,
      },
      {
        source: "/host/settings/notifications",
        destination: "/dashboard/settings/notifications",
        permanent: true,
      },
      {
        source: "/dashboard/merch",
        destination: "/dashboard/merchandise",
        permanent: true,
      },
      {
        source: "/dashboard/merch/:path*",
        destination: "/dashboard/merchandise/:path*",
        permanent: true,
      },
      {
        source: "/dashboard/passport/edit",
        destination: "/dashboard/passport/settings",
        permanent: true,
      },
      {
        source: "/dashboard/ambassadors",
        destination: "/dashboard/ambassador",
        permanent: true,
      },
      {
        source: "/dashboard/ambassadors/:path*",
        destination: "/dashboard/ambassador/:path*",
        permanent: true,
      },
      {
        source: "/sponsors",
        destination: "/sponsorships",
        permanent: true,
      },
      {
        source: "/sponsors/hosts",
        destination: "/sponsorships/hosts",
        permanent: true,
      },
      {
        source: "/admin/sponsors",
        destination: "/admin/sponsorships",
        permanent: true,
      },
      {
        source: "/admin/sponsors/:path*",
        destination: "/admin/sponsorships/:path*",
        permanent: true,
      },
      {
        source: "/guides",
        destination: "/blog",
        permanent: true,
      },
      {
        source: "/guides/:path*",
        destination: "/blog/:path*",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
