import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import {
  API_TIMEOUT_MS,
  createTimeoutSignal,
  isTimeoutError,
} from "@/lib/api-timeouts";

/** Server-side public JSON fetch (RSC / generateMetadata). */
export async function fetchPublicJson<T>(
  path: string,
  init?: RequestInit & { revalidate?: number | false; timeoutMs?: number },
): Promise<{ data: T | null; status: number }> {
  const apiUrl = getApiBaseUrl() || "http://127.0.0.1:8000";
  const apiPrefix = getApiPrefix();
  const suffix = path.startsWith("/") ? path : `/${path}`;
  const revalidate = init?.revalidate;
  const timeoutMs = init?.timeoutMs ?? API_TIMEOUT_MS.public;
  const { timeoutMs: _omit, revalidate: _r, ...rest } = init ?? {};
  void _omit;
  void _r;
  try {
    const signal = createTimeoutSignal(timeoutMs, rest.signal);
    const res = await fetch(`${apiUrl}${apiPrefix}${suffix}`, {
      ...rest,
      signal,
      cache: revalidate === false ? "no-store" : rest.cache,
      next:
        revalidate === false
          ? undefined
          : { revalidate: typeof revalidate === "number" ? revalidate : 120 },
    });
    if (!res.ok) return { data: null, status: res.status };
    return { data: (await res.json()) as T, status: res.status };
  } catch (err) {
    if (isTimeoutError(err) || (err instanceof Error && err.name === "AbortError")) {
      return { data: null, status: 408 };
    }
    return { data: null, status: 0 };
  }
}
