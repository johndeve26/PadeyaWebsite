/**
 * Shared server-side fetch helpers for public Pàdéyá APIs (RSC / ISR).
 * Never use for authenticated or private data.
 *
 * Timeouts must not use AbortSignal on Next `fetch` — that disables the Data
 * Cache and forces dynamic `private, no-store` HTML (always Vercel MISS).
 */

import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import {
  API_TIMEOUT_MS,
  isTimeoutError,
  withTimeoutRace,
} from "@/lib/api-timeouts";

/** Backend origin for RSC — never empty relative `/api` on the server. */
export function publicApiRoot(): string {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  const origin = base || "http://127.0.0.1:8000";
  return `${origin}${prefix}`;
}

export async function fetchPublicJson<T>(
  path: string,
  init?: RequestInit & {
    next?: { revalidate?: number; tags?: string[] };
    timeoutMs?: number;
    /** Explicit no-store for privacy-sensitive public edge cases. */
    cache?: RequestCache;
  },
): Promise<T | null> {
  try {
    const timeoutMs = init?.timeoutMs ?? API_TIMEOUT_MS.public;
    const { timeoutMs: _omit, signal: _signal, ...rest } = init ?? {};
    void _omit;
    void _signal;
    const res = await withTimeoutRace(
      fetch(`${publicApiRoot()}${path}`, { ...rest }),
      timeoutMs,
      () => null,
    );
    if (!res) return null;
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch (err) {
    if (isTimeoutError(err) || (err instanceof Error && err.name === "AbortError")) {
      return null;
    }
    return null;
  }
}
