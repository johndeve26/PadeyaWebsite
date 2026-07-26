import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import {
  API_TIMEOUT_MS,
  isTimeoutError,
  withTimeoutRace,
} from "@/lib/api-timeouts";

/**
 * Server-side public JSON fetch (RSC / generateMetadata).
 *
 * Do **not** pass AbortSignal into Next `fetch` here — that opts out of the
 * Data Cache and forces `Cache-Control: private, no-store` on the HTML route.
 * Timeouts use Promise.race instead.
 *
 * Never use for authenticated / private payloads.
 */
export async function fetchPublicJson<T>(
  path: string,
  init?: RequestInit & { revalidate?: number | false; timeoutMs?: number },
): Promise<{ data: T | null; status: number }> {
  const apiUrl = getApiBaseUrl() || "http://127.0.0.1:8000";
  const apiPrefix = getApiPrefix();
  const suffix = path.startsWith("/") ? path : `/${path}`;
  const revalidate = init?.revalidate;
  const timeoutMs = init?.timeoutMs ?? API_TIMEOUT_MS.public;
  const { timeoutMs: _omit, revalidate: _r, signal: _signal, ...rest } =
    init ?? {};
  void _omit;
  void _r;
  void _signal;
  try {
    const res = await withTimeoutRace(
      fetch(`${apiUrl}${apiPrefix}${suffix}`, {
        ...rest,
        // Never forward caller AbortSignal — keeps Next fetch cacheable.
        cache: revalidate === false ? "no-store" : rest.cache,
        next:
          revalidate === false
            ? undefined
            : { revalidate: typeof revalidate === "number" ? revalidate : 120 },
      }),
      timeoutMs,
      () => null,
    );
    if (!res) return { data: null, status: 408 };
    if (!res.ok) return { data: null, status: res.status };
    return { data: (await res.json()) as T, status: res.status };
  } catch (err) {
    if (isTimeoutError(err) || (err instanceof Error && err.name === "AbortError")) {
      return { data: null, status: 408 };
    }
    return { data: null, status: 0 };
  }
}
