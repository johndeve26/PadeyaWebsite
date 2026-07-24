import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";

/** Server-side public JSON fetch (RSC / generateMetadata). */
export async function fetchPublicJson<T>(
  path: string,
  init?: RequestInit & { revalidate?: number | false },
): Promise<{ data: T | null; status: number }> {
  const apiUrl = getApiBaseUrl() || "http://127.0.0.1:8000";
  const apiPrefix = getApiPrefix();
  const suffix = path.startsWith("/") ? path : `/${path}`;
  const revalidate = init?.revalidate;
  try {
    const res = await fetch(`${apiUrl}${apiPrefix}${suffix}`, {
      ...init,
      cache: revalidate === false ? "no-store" : init?.cache,
      next:
        revalidate === false
          ? undefined
          : { revalidate: typeof revalidate === "number" ? revalidate : 120 },
    });
    if (!res.ok) return { data: null, status: res.status };
    return { data: (await res.json()) as T, status: res.status };
  } catch {
    return { data: null, status: 0 };
  }
}
