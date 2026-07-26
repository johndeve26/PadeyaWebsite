/**
 * Central fetch timeout policy for Pàdéyá API clients.
 *
 * Do not scatter magic numbers — import budgets from here.
 * Mutations are never auto-retried by the shared client (timeouts included).
 */

export const API_TIMEOUT_MS = {
  /** Public marketplace / SSR JSON (events, hosts, sponsors, fans, merch). */
  public: 10_000,
  /** Nav chrome polls (unread counts, lightweight status). */
  chrome: 5_000,
  /** Default authenticated API calls. */
  default: 15_000,
  /**
   * Explicit long operations only (AI, payment init, large uploads).
   * Callers must opt in — never inherit blindly from public/default.
   */
  long: 60_000,
} as const;

export type ApiTimeoutBudget = keyof typeof API_TIMEOUT_MS;

export class TimeoutError extends Error {
  readonly status = 408;
  readonly detail: string;
  readonly timedOut = true as const;

  constructor(detail = "Request timed out. Check your connection and try again.") {
    super(detail);
    this.name = "TimeoutError";
    this.detail = detail;
  }
}

/** Prefer this when surfaces already special-case ApiError.detail. */
export function errorDetail(err: unknown, fallback: string): string {
  if (isTimeoutError(err)) return err.detail;
  if (
    typeof err === "object" &&
    err !== null &&
    "detail" in err &&
    typeof (err as { detail: unknown }).detail === "string"
  ) {
    return (err as { detail: string }).detail;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

export function isTimeoutError(err: unknown): err is TimeoutError {
  return (
    err instanceof TimeoutError ||
    (typeof err === "object" &&
      err !== null &&
      "timedOut" in err &&
      (err as { timedOut?: unknown }).timedOut === true)
  );
}

/** Human copy for marketplace / public error states. */
export function timeoutOrErrorMessage(
  err: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  if (isTimeoutError(err)) {
    return err.detail;
  }
  if (err instanceof Error && err.name === "AbortError") {
    return "Request timed out. Check your connection and try again.";
  }
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return fallback;
}

export function timeoutMsFor(
  budget: ApiTimeoutBudget | number | undefined,
  fallback: number = API_TIMEOUT_MS.default,
): number {
  if (typeof budget === "number" && Number.isFinite(budget) && budget > 0) {
    return budget;
  }
  if (typeof budget === "string" && budget in API_TIMEOUT_MS) {
    return API_TIMEOUT_MS[budget];
  }
  return fallback;
}

/**
 * Build an AbortSignal for a timeout budget.
 * Combines with an optional caller signal via AbortSignal.any when available.
 */
export function createTimeoutSignal(
  ms: number,
  external?: AbortSignal | null,
): AbortSignal {
  const timeoutSignal =
    typeof AbortSignal !== "undefined" &&
    typeof AbortSignal.timeout === "function"
      ? AbortSignal.timeout(ms)
      : (() => {
          const controller = new AbortController();
          const id = setTimeout(() => controller.abort(), ms);
          // Best-effort cleanup if the request finishes early is left to GC.
          void id;
          return controller.signal;
        })();

  if (!external) return timeoutSignal;
  if (typeof AbortSignal !== "undefined" && typeof AbortSignal.any === "function") {
    return AbortSignal.any([timeoutSignal, external]);
  }
  // Fallback: prefer external; timeout still races via AbortSignal.timeout alone
  // when any() is unavailable — attach abort listener.
  const controller = new AbortController();
  const onAbort = () => controller.abort();
  if (timeoutSignal.aborted || external.aborted) {
    controller.abort();
    return controller.signal;
  }
  timeoutSignal.addEventListener("abort", onAbort, { once: true });
  external.addEventListener("abort", onAbort, { once: true });
  return controller.signal;
}

export function mapAbortToTimeoutError(err: unknown): never {
  if (isTimeoutError(err)) throw err;
  if (
    err instanceof Error &&
    (err.name === "AbortError" || err.name === "TimeoutError")
  ) {
    throw new TimeoutError();
  }
  throw err;
}

/**
 * Race a promise against a wall-clock timeout **without** attaching AbortSignal
 * to Next.js `fetch`.
 *
 * Custom AbortSignal opts server fetches out of the Next Data Cache and forces
 * the route into `private, no-store` (always Vercel MISS). Use this for RSC/ISR
 * public fetches; keep `createTimeoutSignal` for browser/authenticated clients.
 */
export async function withTimeoutRace<T>(
  promise: Promise<T>,
  ms: number,
  onTimeout: () => T,
): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      promise,
      new Promise<T>((resolve) => {
        timer = setTimeout(() => resolve(onTimeout()), ms);
      }),
    ]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}
