import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { FanPassportPublicClient } from "@/components/passport/FanPassportPublicClient";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import type { FanPassportPublicPage } from "@/lib/types/passport";

async function loadPublicPassport(
  username: string,
): Promise<FanPassportPublicPage | null> {
  // Prefer API_PROXY_TARGET / NEXT_PUBLIC_API_URL — never a bare relative
  // "/api/…" on the server (that fails when NEXT_PUBLIC_API_URL is empty).
  const apiUrl = getApiBaseUrl() || "http://127.0.0.1:8000";
  const apiPrefix = getApiPrefix();
  try {
    const res = await fetch(
      `${apiUrl}${apiPrefix}/f/${encodeURIComponent(username)}`,
      // Privacy toggles must reflect immediately — do not ISR-cache 404s.
      { cache: "no-store" },
    );
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return (await res.json()) as FanPassportPublicPage;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ username: string }>;
}): Promise<Metadata> {
  const { username } = await params;
  const page = await loadPublicPassport(username);
  if (!page) {
    return { title: "Fan Passport | Pàdéyá" };
  }
  return {
    title: `${page.display_name} · Fan Passport | Pàdéyá`,
    description:
      page.tagline ||
      `${page.display_name}'s Fan Passport on Pàdéyá — verified nights, badges, and hosts.`,
  };
}

export default async function PublicFanPassportPage({
  params,
}: {
  params: Promise<{ username: string }>;
}) {
  const { username } = await params;
  const page = await loadPublicPassport(username);
  if (!page) notFound();
  return <FanPassportPublicClient initial={page} />;
}
