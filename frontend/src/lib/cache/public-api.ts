/**
 * Shared server-side fetch helpers for public Pàdéyá APIs (RSC / ISR).
 * Never use for authenticated or private data.
 *
 * Runtime timeouts must not use AbortSignal on Next `fetch` — that disables the
 * Data Cache and forces dynamic `private, no-store` HTML (always Vercel MISS).
 *
 * Production builds are different: a hung origin leaves the underlying `fetch`
 * pending after `Promise.race`, and Next SSG workers stay busy until the socket
 * dies — exceeding staticPageGenerationTimeout. Abort during build only.
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

/** True while `next build` is collecting / generating static pages. */
export function isNextProductionBuild(): boolean {
  return (
    process.env.NEXT_PHASE === "phase-production-build" ||
    process.env.PADEYA_SSG_ABORT_FETCH === "1"
  );
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
    const url = `${publicApiRoot()}${path}`;

    // Build: cancel the socket so SSG workers are not held by orphaned fetches.
    // Runtime: race without AbortSignal so ISR / Data Cache stay intact.
    const res = isNextProductionBuild()
      ? await fetch(url, {
          ...rest,
          cache: "no-store",
          signal: AbortSignal.timeout(timeoutMs),
        }).catch(() => null)
      : await withTimeoutRace(
          fetch(url, { ...rest }),
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
