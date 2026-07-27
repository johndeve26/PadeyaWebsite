import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  isImpersonationSession,
  setTokens,
} from "@/lib/auth/storage";
import { shouldRefreshAccessToken } from "@/lib/auth/jwt";
import {
  DEFAULT_SESSION_EXPIRED_MESSAGE,
  markSessionExpired,
} from "@/lib/auth/session-expired";
import type {
  AuthTokens,
  ImpersonationDurationMinutes,
  ImpersonationEndResponse,
  ImpersonationHistoryItem,
  ImpersonationStartResponse,
  ImpersonationStatusResponse,
  User,
} from "@/lib/auth/types";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import {
  type ApiTimeoutBudget,
  createTimeoutSignal,
  mapAbortToTimeoutError,
  timeoutMsFor,
} from "@/lib/api-timeouts";

const API_URL = getApiBaseUrl();
const API_PREFIX = getApiPrefix();

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

export {
  TimeoutError,
  API_TIMEOUT_MS,
  isTimeoutError,
  timeoutOrErrorMessage,
} from "@/lib/api-timeouts";

type RequestOptions = {
  method?: string;
  body?: unknown;
  auth?: boolean;
  skipRefresh?: boolean;
  /** Named budget or explicit milliseconds. */
  timeout?: ApiTimeoutBudget | number;
  signal?: AbortSignal;
};

const CHROME_PATH_PREFIXES = [
  "/notifications/unread-count",
  "/messages/unread-count",
] as const;

function defaultBudgetFor(
  path: string,
  method: string,
  options: RequestOptions,
): ApiTimeoutBudget | number {
  if (options.timeout !== undefined) return options.timeout;
  if (CHROME_PATH_PREFIXES.some((p) => path.startsWith(p))) {
    return "chrome";
  }
  // Auth refresh stays on default — not chrome poll.
  if (path.startsWith("/auth/")) return "default";
  if (method === "GET" && options.auth === false) return "public";
  return "default";
}

type FastApiValidationItem = {
  msg?: string;
  loc?: Array<string | number>;
  type?: string;
};

function formatValidationItem(item: FastApiValidationItem): string {
  const msg = (item.msg || "Invalid value")
    .replace(/^Value error,\s*/i, "")
    .trim();
  const loc = (item.loc || []).filter((part) => part !== "body");
  if (loc.length === 0) return msg;

  const human: string[] = [];
  for (let i = 0; i < loc.length; i += 1) {
    const part = loc[i];
    const next = loc[i + 1];
    if (typeof part === "string" && typeof next === "number") {
      const label = part.replace(/_/g, " ");
      human.push(`${label} ${next + 1}`);
      i += 1;
      continue;
    }
    if (typeof part === "string") {
      human.push(part.replace(/_/g, " "));
    } else if (typeof part === "number") {
      human.push(`item ${part + 1}`);
    }
  }
  const where = human.join(" → ");
  return where ? `${where}: ${msg}` : msg;
}

async function parseError(response: Response): Promise<ApiError> {
  let detail = response.statusText || "Request failed";
  try {
    const data = (await response.json()) as {
      detail?: string | FastApiValidationItem[] | { message?: string };
    };
    if (typeof data.detail === "string") {
      detail = data.detail;
    } else if (Array.isArray(data.detail) && data.detail.length > 0) {
      detail = data.detail
        .slice(0, 3)
        .map((item) => formatValidationItem(item))
        .join(" · ");
      if (data.detail.length > 3) {
        detail += ` · +${data.detail.length - 3} more`;
      }
    } else if (
      data.detail &&
      typeof data.detail === "object" &&
      !Array.isArray(data.detail) &&
      typeof data.detail.message === "string"
    ) {
      detail = data.detail.message;
    }
  } catch {
    // ignore non-JSON error bodies
  }
  if (
    response.status === 503 &&
    typeof detail === "string" &&
    (detail.includes("dev/log mode") || detail.includes("Email sending is disabled"))
  ) {
    return new ApiError(response.status, detail);
  }
  if (
    (detail === "Request failed" || !detail.trim()) &&
    response.status >= 500
  ) {
    detail =
      "Server error — the API may need a database migration or redeploy. Try again shortly or contact support.";
  } else if (detail === "Request failed" && response.status > 0) {
    detail = `Request failed (${response.status}). Check your connection and try again.`;
  }
  return new ApiError(response.status, detail);
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (options.auth !== false) {
    const access = getAccessToken();
    if (access) {
      headers.Authorization = `Bearer ${access}`;
    }
  }

  const method = options.method ?? (options.body ? "POST" : "GET");
  const timeoutMs = timeoutMsFor(defaultBudgetFor(path, method, options));
  const signal = createTimeoutSignal(timeoutMs, options.signal);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${API_PREFIX}${path}`, {
      method,
      headers,
      signal,
      // Callers may pass an object (preferred) or a pre-stringified JSON body.
      body:
        options.body === undefined || options.body === null
          ? undefined
          : typeof options.body === "string"
            ? options.body
            : JSON.stringify(options.body),
    });
  } catch (err) {
    mapAbortToTimeoutError(err);
  }

  if (
    response.status === 401 &&
    options.auth !== false &&
    !options.skipRefresh &&
    getRefreshToken() &&
    !isImpersonationSession()
  ) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      // Single refresh retry only — never auto-retry mutations on timeout.
      return apiRequest<T>(path, { ...options, skipRefresh: true });
    }
    markSessionExpired(DEFAULT_SESSION_EXPIRED_MESSAGE);
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

function filenameFromContentDisposition(
  header: string | null,
  fallback: string,
): string {
  if (!header) return fallback;
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (utf8?.[1]) {
    try {
      return decodeURIComponent(utf8[1].trim());
    } catch {
      // fall through
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain?.[1]?.trim() || fallback;
}

/** Authenticated binary download (PDF, etc.) — triggers a browser save dialog. */
export async function apiDownload(
  path: string,
  options: {
    auth?: boolean;
    skipRefresh?: boolean;
    fallbackFilename?: string;
    timeout?: ApiTimeoutBudget | number;
    signal?: AbortSignal;
  } = {},
): Promise<{ filename: string; blob: Blob }> {
  const headers: Record<string, string> = {};
  if (options.auth !== false) {
    const access = getAccessToken();
    if (access) {
      headers.Authorization = `Bearer ${access}`;
    }
  }

  const timeoutMs = timeoutMsFor(options.timeout ?? "long");
  const signal = createTimeoutSignal(timeoutMs, options.signal);
  let response: Response;
  try {
    response = await fetch(`${API_URL}${API_PREFIX}${path}`, {
      method: "GET",
      headers,
      signal,
    });
  } catch (err) {
    mapAbortToTimeoutError(err);
  }

  if (
    response.status === 401 &&
    options.auth !== false &&
    !options.skipRefresh &&
    getRefreshToken() &&
    !isImpersonationSession()
  ) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      return apiDownload(path, { ...options, skipRefresh: true });
    }
    markSessionExpired(DEFAULT_SESSION_EXPIRED_MESSAGE);
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  const blob = await response.blob();
  const filename = filenameFromContentDisposition(
    response.headers.get("Content-Disposition"),
    options.fallbackFilename ?? "download",
  );
  return { filename, blob };
}

/** Multipart upload helper (do not set Content-Type — browser sets boundary). */
export async function apiUpload<T>(
  path: string,
  formData: FormData,
  options: {
    auth?: boolean;
    skipRefresh?: boolean;
    timeout?: ApiTimeoutBudget | number;
    signal?: AbortSignal;
  } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.auth !== false) {
    const access = getAccessToken();
    if (access) {
      headers.Authorization = `Bearer ${access}`;
    }
  }

  // Uploads often need a longer budget — callers may override.
  const timeoutMs = timeoutMsFor(options.timeout ?? "long");
  const signal = createTimeoutSignal(timeoutMs, options.signal);
  let response: Response;
  try {
    response = await fetch(`${API_URL}${API_PREFIX}${path}`, {
      method: "POST",
      headers,
      body: formData,
      signal,
    });
  } catch (err) {
    mapAbortToTimeoutError(err);
  }

  if (
    response.status === 401 &&
    options.auth !== false &&
    !options.skipRefresh &&
    getRefreshToken() &&
    !isImpersonationSession()
  ) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      return apiUpload<T>(path, formData, { ...options, skipRefresh: true });
    }
    markSessionExpired(DEFAULT_SESSION_EXPIRED_MESSAGE);
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as T;
}

/**
 * Single-flight refresh. Backend rotates refresh tokens; concurrent
 * `/auth/refresh` calls can revoke a just-issued token and clearTokens()
 * the good session — which surfaces as "Invalid or expired access token"
 * on host workspace loads.
 */
let refreshInFlight: Promise<AuthTokens | null> | null = null;

export async function refreshTokens(): Promise<AuthTokens | null> {
  if (refreshInFlight) {
    return refreshInFlight;
  }

  refreshInFlight = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      return null;
    }

    try {
      const tokens = await apiRequest<AuthTokens>("/auth/refresh", {
        method: "POST",
        body: { refresh_token: refreshToken },
        auth: false,
        skipRefresh: true,
      });
      setTokens(tokens);
      return tokens;
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        markSessionExpired(DEFAULT_SESSION_EXPIRED_MESSAGE);
        clearTokens();
      }
      return null;
    }
  })().finally(() => {
    refreshInFlight = null;
  });

  return refreshInFlight;
}

/** Proactively refresh when access JWT is missing or near expiry. */
export async function ensureAccessTokenFresh(): Promise<boolean> {
  if (isImpersonationSession()) {
    return Boolean(getAccessToken());
  }
  const refresh = getRefreshToken();
  if (!refresh) {
    return false;
  }
  const access = getAccessToken();
  if (access && !shouldRefreshAccessToken(access)) {
    return true;
  }
  const tokens = await refreshTokens();
  return Boolean(tokens);
}

export async function registerRequest(input: {
  email: string;
  password: string;
  username: string;
}): Promise<AuthTokens> {
  return apiRequest<AuthTokens>("/auth/register", {
    method: "POST",
    body: input,
    auth: false,
  });
}

export async function requestPasswordReset(email: string): Promise<string> {
  const data = await apiRequest<{ message?: string }>(
    "/auth/password-reset/request",
    {
      method: "POST",
      body: { email: email.trim().toLowerCase() },
      auth: false,
    },
  );
  return data.message?.trim() || "";
}

export async function verifyPasswordReset(input: {
  email: string;
  code: string;
}): Promise<string> {
  const data = await apiRequest<{ message?: string }>(
    "/auth/password-reset/verify",
    {
      method: "POST",
      body: {
        email: input.email.trim().toLowerCase(),
        code: input.code.trim().toUpperCase().replace(/[\s-]/g, ""),
      },
      auth: false,
    },
  );
  return data.message?.trim() || "";
}

export async function confirmPasswordReset(input: {
  email: string;
  code: string;
  new_password: string;
}): Promise<string> {
  const data = await apiRequest<{ message?: string }>(
    "/auth/password-reset/confirm",
    {
      method: "POST",
      body: {
        email: input.email.trim().toLowerCase(),
        code: input.code.trim().toUpperCase().replace(/[\s-]/g, ""),
        new_password: input.new_password,
      },
      auth: false,
    },
  );
  return data.message?.trim() || "";
}

export async function requestEmailVerification(): Promise<string> {
  const data = await apiRequest<{ message?: string }>(
    "/auth/email/verify/request",
    {
      method: "POST",
      body: {},
    },
  );
  return data.message?.trim() || "";
}

export async function confirmEmailVerification(input: {
  token?: string;
  code?: string;
}): Promise<AuthTokens> {
  const body: { token?: string; code?: string } = {};
  const token = input.token?.trim();
  const code = input.code?.trim().toUpperCase().replace(/[\s-]/g, "");
  if (token) body.token = token;
  if (code) body.code = code;
  const tokens = await apiRequest<AuthTokens>("/auth/email/verify/confirm", {
    method: "POST",
    body,
    auth: Boolean(code && !token),
  });
  setTokens(tokens);
  return tokens;
}

export async function changePassword(input: {
  current_password: string;
  new_password: string;
}): Promise<void> {
  const refresh = getRefreshToken();
  await apiRequest<{ message?: string }>("/auth/change-password", {
    method: "POST",
    body: {
      ...input,
      ...(refresh ? { refresh_token: refresh } : {}),
    },
  });
}

export async function changeEmail(input: {
  new_email: string;
  current_password: string;
}): Promise<
  | { status: "pending"; message: string; pending_email: string }
  | { status: "updated"; user: User }
> {
  const data = await apiRequest<
    | { message?: string; pending_email?: string }
    | User
  >("/auth/change-email", {
    method: "POST",
    body: {
      new_email: input.new_email.trim().toLowerCase(),
      current_password: input.current_password,
    },
  });
  if (
    data &&
    typeof data === "object" &&
    "pending_email" in data &&
    typeof data.pending_email === "string"
  ) {
    return {
      status: "pending",
      message:
        (typeof data.message === "string" && data.message) ||
        "Enter the confirmation code sent to your new email.",
      pending_email: data.pending_email,
    };
  }
  return { status: "updated", user: data as User };
}

export async function confirmEmailChange(input: {
  code: string;
}): Promise<User> {
  const refresh = getRefreshToken();
  return apiRequest<User>("/auth/change-email/confirm", {
    method: "POST",
    body: {
      code: input.code.trim().toUpperCase().replace(/[\s-]/g, ""),
      ...(refresh ? { refresh_token: refresh } : {}),
    },
  });
}

export async function loginRequest(input: {
  login: string;
  password: string;
}): Promise<AuthTokens> {
  return apiRequest<AuthTokens>("/auth/login", {
    method: "POST",
    body: input,
    auth: false,
  });
}

export async function logoutRequest(): Promise<void> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    clearTokens();
    return;
  }
  try {
    await apiRequest("/auth/logout", {
      method: "POST",
      body: { refresh_token: refreshToken },
      skipRefresh: true,
    });
  } finally {
    clearTokens();
  }
}

export async function fetchMe(): Promise<User> {
  return apiRequest<User>("/auth/me");
}

export async function startImpersonationRequest(input: {
  user_id: string;
  reason: string;
  support_ticket_id?: string;
  duration_minutes?: ImpersonationDurationMinutes;
}): Promise<ImpersonationStartResponse> {
  const { user_id, ...body } = input;
  return apiRequest<ImpersonationStartResponse>(
    `/admin/users/${encodeURIComponent(user_id)}/impersonation/start`,
    {
      method: "POST",
      body,
    },
  );
}

export async function endImpersonationRequest(): Promise<ImpersonationEndResponse> {
  return apiRequest<ImpersonationEndResponse>("/admin/impersonation/end", {
    method: "POST",
    skipRefresh: true,
  });
}

/** @deprecated Use endImpersonationRequest */
export async function stopImpersonationRequest(): Promise<ImpersonationEndResponse> {
  return endImpersonationRequest();
}

export async function fetchImpersonationStatus(): Promise<ImpersonationStatusResponse> {
  return apiRequest<ImpersonationStatusResponse>("/me/impersonation");
}

export async function fetchImpersonationHistory(
  userId: string,
  opts?: { limit?: number; offset?: number },
): Promise<ImpersonationHistoryItem[]> {
  const params = new URLSearchParams();
  if (opts?.limit != null) params.set("limit", String(opts.limit));
  if (opts?.offset != null) params.set("offset", String(opts.offset));
  const qs = params.toString();
  return apiRequest<ImpersonationHistoryItem[]>(
    `/admin/users/${encodeURIComponent(userId)}/impersonation/history${
      qs ? `?${qs}` : ""
    }`,
  );
}
