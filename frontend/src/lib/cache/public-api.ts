/**
 * Shared server-side fetch helpers for public Pàdéyá APIs (RSC / ISR).
 * Never use for authenticated or private data.
 */

import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import {
  API_TIMEOUT_MS,
  createTimeoutSignal,
  isTimeoutError,
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
  },
): Promise<T | null> {
  try {
    const timeoutMs = init?.timeoutMs ?? API_TIMEOUT_MS.public;
    const { timeoutMs: _omit, ...rest } = init ?? {};
    void _omit;
    const signal = createTimeoutSignal(timeoutMs, rest.signal);
    const res = await fetch(`${publicApiRoot()}${path}`, { ...rest, signal });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch (err) {
    if (isTimeoutError(err) || (err instanceof Error && err.name === "AbortError")) {
      return null;
    }
    return null;
  }
}
