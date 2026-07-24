import type { Metadata } from "next";

import { brand } from "@/lib/brand";

/** Canonical live site — used for shareable links when env is missing/local. */
export const LIVE_SITE_ORIGIN = "https://padeya.com";

function isLocalOrigin(origin: string): boolean {
  try {
    const host = new URL(origin).hostname;
    return (
      host === "localhost" ||
      host === "127.0.0.1" ||
      host === "0.0.0.0" ||
      host.endsWith(".local")
    );
  } catch {
    return /localhost|127\.0\.0\.1/i.test(origin);
  }
}

function originFromApiUrl(apiUrl: string): string | null {
  try {
    const u = new URL(apiUrl);
    if (isLocalOrigin(u.origin)) return null;
    if (u.hostname.startsWith("api.")) {
      u.hostname = u.hostname.slice(4);
    }
    return u.origin;
  } catch {
    return null;
  }
}

export function siteOrigin(): string {
  const raw =
    process.env.NEXT_PUBLIC_SITE_URL ||
    process.env.SITE_URL ||
    "http://localhost:3000";
  return raw.replace(/\/$/, "");
}

/**
 * Public origin for shareable links (referral, OG, emails in the browser).
 * Prefers configured site URL, then the current non-local window origin,
 * then derives from NEXT_PUBLIC_API_URL, then the live brand domain.
 */
export function publicShareOrigin(): string {
  const configured = (
    process.env.NEXT_PUBLIC_SITE_URL ||
    process.env.SITE_URL ||
    ""
  ).replace(/\/$/, "");
  if (configured && !isLocalOrigin(configured)) return configured;

  if (typeof window !== "undefined") {
    const current = window.location.origin;
    if (current && !isLocalOrigin(current)) return current;
  }

  const fromApi = originFromApiUrl(
    process.env.NEXT_PUBLIC_API_URL?.trim() || "",
  );
  if (fromApi) return fromApi;

  return LIVE_SITE_ORIGIN;
}

export function absoluteUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${siteOrigin()}${p}`;
}

export function defaultOgImage(): string {
  return absoluteUrl("/brand/padeya-og.png");
}

export function buildPageMetadata(opts: {
  title: string;
  description: string;
  path: string;
  image?: string | null;
  noIndex?: boolean;
}): Metadata {
  const url = absoluteUrl(opts.path);
  const image = opts.image || defaultOgImage();
  return {
    title: opts.title,
    description: opts.description,
    alternates: { canonical: url },
    robots: opts.noIndex ? { index: false, follow: false } : undefined,
    openGraph: {
      title: opts.title,
      description: opts.description,
      url,
      siteName: brand.name,
      images: [{ url: image }],
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: opts.title,
      description: opts.description,
      images: [image],
    },
  };
}
