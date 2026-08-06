"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { getAssistantSession, streamAssistantChat } from "@/lib/assistant-api";
import type {
  AssistantAction,
  AssistantCard,
  AssistantChatMessage,
  AssistantCitation,
  AssistantDonePayload,
  AssistantPageContext,
  AssistantSseEvent,
} from "@/lib/types/assistant";

const SESSION_STORAGE_KEY = "padeya-assistant-session-id";

function readStoredSessionId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(SESSION_STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStoredSessionId(sessionId: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (sessionId) {
      window.sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
    } else {
      window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
    }
  } catch {
    // ignore
  }
}

function localId(prefix: string): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function asCard(data: Record<string, unknown>): AssistantCard | null {
  if (typeof data.title !== "string" || typeof data.type !== "string") return null;
  return {
    type: data.type,
    title: data.title,
    subtitle: typeof data.subtitle === "string" ? data.subtitle : null,
    url: typeof data.url === "string" ? data.url : null,
    image_url: typeof data.image_url === "string" ? data.image_url : null,
    meta:
      data.meta && typeof data.meta === "object"
        ? (data.meta as Record<string, unknown>)
        : {},
  };
}

function asAction(data: Record<string, unknown>): AssistantAction | null {
  if (typeof data.label !== "string" || typeof data.type !== "string") return null;
  return {
    type: data.type,
    label: data.label,
    route_key: typeof data.route_key === "string" ? data.route_key : null,
    url: typeof data.url === "string" ? data.url : null,
    tool_name: typeof data.tool_name === "string" ? data.tool_name : null,
    confirmation_id:
      typeof data.confirmation_id === "string" ? data.confirmation_id : null,
    requires_confirmation: Boolean(data.requires_confirmation),
    meta:
      data.meta && typeof data.meta === "object"
        ? (data.meta as Record<string, unknown>)
        : {},
  };
}

function asCitation(data: Record<string, unknown>): AssistantCitation | null {
  if (typeof data.title !== "string" || typeof data.url !== "string") return null;
  return {
    title: data.title,
    url: data.url,
    snippet: typeof data.snippet === "string" ? data.snippet : null,
    source_type: typeof data.source_type === "string" ? data.source_type : null,
    route_key: typeof data.route_key === "string" ? data.route_key : null,
  };
}

export type UseAssistantChatOptions = {
  pageContext?: AssistantPageContext | null;
  aiProviderReady?: boolean;
  onMessageSent?: () => void;
  onError?: (message: string) => void;
};

export function useAssistantChat(options: UseAssistantChatOptions = {}) {
  const [messages, setMessages] = useState<AssistantChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(() => readStoredSessionId());
  const [productName, setProductName] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [statusPhase, setStatusPhase] = useState<string | null>(null);
  const [online, setOnline] = useState(options.aiProviderReady ?? true);
  const abortRef = useRef<AbortController | null>(null);
  const assistantDraftId = useRef<string | null>(null);
  const pageContextRef = useRef(options.pageContext);
  const onMessageSentRef = useRef(options.onMessageSent);
  const onErrorRef = useRef(options.onError);

  useEffect(() => {
    pageContextRef.current = options.pageContext;
    onMessageSentRef.current = options.onMessageSent;
    onErrorRef.current = options.onError;
  }, [options.pageContext, options.onMessageSent, options.onError]);

  useEffect(() => {
    setOnline(options.aiProviderReady ?? true);
  }, [options.aiProviderReady]);

  useEffect(() => {
    const stored = readStoredSessionId();
    if (!stored || messages.length > 0) return;
    let cancelled = false;
    void getAssistantSession(stored)
      .then((detail) => {
        if (cancelled) return;
        setSessionId(stored);
        setMessages(
          (detail.messages ?? []).map((m) => ({
            id: m.id,
            role: m.role as AssistantChatMessage["role"],
            content: m.content,
            citations: (m.structured_content_json?.citations as AssistantCitation[]) ?? [],
            cards: (m.structured_content_json?.cards as AssistantCard[]) ?? [],
            actions: (m.structured_content_json?.actions as AssistantAction[]) ?? [],
          })),
        );
      })
      .catch(() => {
        writeStoredSessionId(null);
        setSessionId(null);
      });
    return () => {
      cancelled = true;
    };
  }, [messages.length]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setStatusPhase(null);
    if (assistantDraftId.current) {
      const id = assistantDraftId.current;
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, streaming: false } : m)),
      );
    }
  }, []);

  const resetSession = useCallback(() => {
    stop();
    setMessages([]);
    setSessionId(null);
    writeStoredSessionId(null);
    setProductName(null);
    setStatusPhase(null);
    assistantDraftId.current = null;
  }, [stop]);

  const applySseEvent = useCallback((event: AssistantSseEvent, draftId: string) => {
    const { event: type, data } = event;

    if (type === "session") {
      if (typeof data.session_id === "string") {
        setSessionId(data.session_id);
        writeStoredSessionId(data.session_id);
      }
      if (typeof data.product_name === "string") {
        setProductName(data.product_name);
      }
      return;
    }

    if (type === "status") {
      if (typeof data.phase === "string") setStatusPhase(data.phase);
      return;
    }

    if (type === "token") {
      const chunk =
        typeof data.text === "string"
          ? data.text
          : typeof data.value === "string"
            ? data.value
            : "";
      if (!chunk) return;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === draftId
            ? { ...m, content: m.content + chunk, streaming: true }
            : m,
        ),
      );
      return;
    }

    if (type === "card") {
      const card = asCard(data);
      if (!card) return;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === draftId ? { ...m, cards: [...(m.cards ?? []), card] } : m,
        ),
      );
      return;
    }

    if (type === "action") {
      const action = asAction(data);
      if (!action) return;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === draftId
            ? { ...m, actions: [...(m.actions ?? []), action] }
            : m,
        ),
      );
      return;
    }

    if (type === "citation") {
      const citation = asCitation(data);
      if (!citation) return;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === draftId
            ? { ...m, citations: [...(m.citations ?? []), citation] }
            : m,
        ),
      );
      return;
    }

    if (type === "error") {
      const detail =
        typeof data.detail === "string"
          ? data.detail
          : "Something went wrong. Please try again.";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === draftId
            ? {
                ...m,
                content: m.content || detail,
                error: true,
                streaming: false,
              }
            : m,
        ),
      );
      onErrorRef.current?.(detail);
      return;
    }

    if (type === "done") {
      const done = data as AssistantDonePayload;
      if (typeof done.session_id === "string") setSessionId(done.session_id);
      if (typeof done.product_name === "string") {
        setProductName(done.product_name);
      }
      setMessages((prev) =>
        prev.map((m) => {
          if (m.id !== draftId) return m;
          const usedFallback = done.used_fallback ?? m.usedFallback;
          if (usedFallback) setOnline(false);
          return {
            ...m,
            content: done.text?.trim() ? done.text : m.content,
            streaming: false,
            messageId: done.message_id ?? m.messageId,
            citations: done.citations?.length ? done.citations : m.citations,
            cards: done.cards?.length ? done.cards : m.cards,
            actions: done.actions?.length ? done.actions : m.actions,
            confirmationId: done.confirmation_id ?? m.confirmationId,
            safetyStatus: done.safety_status ?? m.safetyStatus,
            usedFallback,
            error: done.ok === false ? true : m.error,
          };
        }),
      );
    }
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || streaming) return;

      const userMsg: AssistantChatMessage = {
        id: localId("user"),
        role: "user",
        content: trimmed,
      };
      const draftId = localId("asst");
      assistantDraftId.current = draftId;
      const assistantMsg: AssistantChatMessage = {
        id: draftId,
        role: "assistant",
        content: "",
        streaming: true,
        cards: [],
        actions: [],
        citations: [],
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setStreaming(true);
      setStatusPhase("starting");
      setOnline(options.aiProviderReady ?? true);
      onMessageSentRef.current?.();

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const timezone =
          typeof Intl !== "undefined"
            ? Intl.DateTimeFormat().resolvedOptions().timeZone
            : null;

        await streamAssistantChat(
          {
            message: trimmed,
            session_id: sessionId,
            page_context: pageContextRef.current ?? null,
            timezone,
          },
          {
            signal: controller.signal,
            onEvent: (ev) => applySseEvent(ev, draftId),
          },
        );
      } catch (err) {
        if (controller.signal.aborted) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === draftId
                ? {
                    ...m,
                    streaming: false,
                    content: m.content || "Stopped.",
                  }
                : m,
            ),
          );
        } else {
          setOnline(false);
          const detail =
            err instanceof Error ? err.message : "Assistant unavailable";
          setMessages((prev) =>
            prev.map((m) =>
              m.id === draftId
                ? {
                    ...m,
                    streaming: false,
                    error: true,
                    content: m.content || detail,
                  }
                : m,
            ),
          );
          onErrorRef.current?.(detail);
        }
      } finally {
        setStreaming(false);
        setStatusPhase(null);
        abortRef.current = null;
      }
    },
    [applySseEvent, sessionId, streaming],
  );

  return {
    messages,
    sessionId,
    productName,
    streaming,
    statusPhase,
    online,
    sendMessage,
    stop,
    resetSession,
  };
}
