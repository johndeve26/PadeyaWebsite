import { getAccessToken } from "@/lib/auth/storage";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import type {
  AssistantChatRequest,
  AssistantDonePayload,
  AssistantFeedbackCreate,
  AssistantSession,
  AssistantSessionDetail,
  AssistantSseEvent,
  AssistantStatus,
} from "@/lib/types/assistant";

function assistantUrl(path: string): string {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  return `${base}${prefix}/assistant${path}`;
}

function authHeaders(includeJson = true): HeadersInit {
  const headers: Record<string, string> = {};
  if (includeJson) headers["Content-Type"] = "application/json";
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function parseJsonError(response: Response): Promise<Error> {
  let detail = response.statusText || "Request failed";
  try {
    const data = (await response.json()) as { detail?: string };
    if (typeof data.detail === "string" && data.detail.trim()) {
      detail = data.detail;
    }
  } catch {
    // ignore
  }
  return new Error(detail);
}

/** Feature-flag / availability probe — no auth required. */
export async function fetchAssistantStatus(
  signal?: AbortSignal,
): Promise<AssistantStatus> {
  const response = await fetch(assistantUrl("/status"), {
    method: "GET",
    credentials: "include",
    cache: "no-store",
    signal,
  });
  if (!response.ok) throw await parseJsonError(response);
  return (await response.json()) as AssistantStatus;
}

export async function listAssistantSessions(
  signal?: AbortSignal,
): Promise<AssistantSession[]> {
  const response = await fetch(assistantUrl("/sessions"), {
    method: "GET",
    credentials: "include",
    headers: authHeaders(false),
    cache: "no-store",
    signal,
  });
  if (!response.ok) throw await parseJsonError(response);
  return (await response.json()) as AssistantSession[];
}

export async function getAssistantSession(
  sessionId: string,
  signal?: AbortSignal,
): Promise<AssistantSessionDetail> {
  const response = await fetch(assistantUrl(`/sessions/${sessionId}`), {
    method: "GET",
    credentials: "include",
    headers: authHeaders(false),
    cache: "no-store",
    signal,
  });
  if (!response.ok) throw await parseJsonError(response);
  return (await response.json()) as AssistantSessionDetail;
}

export async function deleteAssistantSession(
  sessionId: string,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(assistantUrl(`/sessions/${sessionId}`), {
    method: "DELETE",
    credentials: "include",
    headers: authHeaders(false),
    signal,
  });
  if (!response.ok) throw await parseJsonError(response);
}

export async function confirmAssistantAction(
  confirmationId: string,
  idempotencyKey?: string,
  signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  const response = await fetch(
    assistantUrl(`/actions/${confirmationId}/confirm`),
    {
      method: "POST",
      credentials: "include",
      headers: authHeaders(),
      body: JSON.stringify({
        idempotency_key: idempotencyKey ?? null,
      }),
      signal,
    },
  );
  if (!response.ok) throw await parseJsonError(response);
  return (await response.json()) as Record<string, unknown>;
}

export async function cancelAssistantAction(
  confirmationId: string,
  signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  const response = await fetch(
    assistantUrl(`/actions/${confirmationId}/cancel`),
    {
      method: "POST",
      credentials: "include",
      headers: authHeaders(),
      signal,
    },
  );
  if (!response.ok) throw await parseJsonError(response);
  return (await response.json()) as Record<string, unknown>;
}

export async function submitAssistantFeedback(
  payload: AssistantFeedbackCreate,
  signal?: AbortSignal,
): Promise<{ id: string; status: string }> {
  const response = await fetch(assistantUrl("/feedback"), {
    method: "POST",
    credentials: "include",
    headers: authHeaders(),
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok) throw await parseJsonError(response);
  return (await response.json()) as { id: string; status: string };
}

export type StreamChatHandlers = {
  onEvent: (event: AssistantSseEvent) => void;
  signal?: AbortSignal;
};

/**
 * Stream a chat turn via SSE (fetch + ReadableStream).
 * Does not use EventSource so we can POST + Authorization.
 */
export async function streamAssistantChat(
  request: AssistantChatRequest,
  handlers: StreamChatHandlers,
): Promise<AssistantDonePayload | null> {
  const response = await fetch(assistantUrl("/chat/stream"), {
    method: "POST",
    credentials: "include",
    headers: {
      ...authHeaders(),
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      message: request.message,
      session_id: request.session_id ?? null,
      page_context: request.page_context ?? null,
      timezone: request.timezone ?? null,
    }),
    signal: handlers.signal,
  });

  if (!response.ok) {
    throw await parseJsonError(response);
  }
  if (!response.body) {
    throw new Error("Assistant stream unavailable");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let donePayload: AssistantDonePayload | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const parsed = parseSseBlock(raw);
      if (!parsed) continue;
      handlers.onEvent(parsed);
      if (parsed.event === "done") {
        donePayload = parsed.data as AssistantDonePayload;
      }
    }
  }

  if (buffer.trim()) {
    const parsed = parseSseBlock(buffer);
    if (parsed) {
      handlers.onEvent(parsed);
      if (parsed.event === "done") {
        donePayload = parsed.data as AssistantDonePayload;
      }
    }
  }

  return donePayload;
}

function parseSseBlock(block: string): AssistantSseEvent | null {
  const lines = block.split(/\r?\n/);
  let event = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (!line || line.startsWith(":")) continue;
    if (line.startsWith("event:")) {
      event = line.slice(6).trim() || "message";
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (dataLines.length === 0) return null;
  const raw = dataLines.join("\n");
  let data: Record<string, unknown>;
  try {
    const parsed = JSON.parse(raw) as unknown;
    data =
      parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : { value: parsed };
  } catch {
    data = { text: raw };
  }
  return { event, data };
}

/** Whether the launcher should render for the current auth + status. */
export function isAssistantVisibleForUser(
  status: AssistantStatus | null,
  isAuthenticated: boolean,
): boolean {
  if (!status?.assistant_enabled) return false;
  if (isAuthenticated) {
    return status.authenticated_enabled || status.public_enabled;
  }
  return status.public_enabled;
}
