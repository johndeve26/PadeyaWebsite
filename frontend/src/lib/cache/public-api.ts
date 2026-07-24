/**
 * Shared server-side fetch helpers for public Pàdéyá APIs (RSC / ISR).
 * Never use for authenticated or private data.
 */

import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";

/** Backend origin for RSC — never empty relative `/api` on the server. */
export function publicApiRoot(): string {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  const origin = base || "http://127.0.0.1:8000";
  return `${origin}${prefix}`;
}

export async function fetchPublicJson<T>(
  path: string,
  init?: RequestInit & { next?: { revalidate?: number; tags?: string[] } },
): Promise<T | null> {
  try {
    const res = await fetch(`${publicApiRoot()}${path}`, init);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
