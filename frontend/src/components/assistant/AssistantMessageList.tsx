"use client";

import { useEffect, useRef } from "react";

import { AssistantMessage } from "@/components/assistant/AssistantMessage";
import { AssistantWelcome } from "@/components/assistant/AssistantWelcome";
import type {
  AssistantChatMessage,
  AssistantSuggestedPrompt,
} from "@/lib/types/assistant";

export function AssistantMessageList({
  messages,
  role,
  productTitle,
  subtitle,
  statusPhase,
  onSelectPrompt,
}: {
  messages: AssistantChatMessage[];
  role: string | null;
  productTitle: string;
  subtitle: string;
  statusPhase?: string | null;
  onSelectPrompt: (prompt: AssistantSuggestedPrompt) => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const liveRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, statusPhase]);

  const lastAssistant = [...messages]
    .reverse()
    .find((m) => m.role === "assistant" && !m.streaming);
  const liveText = lastAssistant?.content?.slice(0, 280) ?? "";

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-3 sm:px-5">
      <div aria-live="polite" aria-atomic="false" className="sr-only" ref={liveRef}>
        {liveText}
      </div>

      {messages.length === 0 ? (
        <AssistantWelcome
          role={role}
          productTitle={productTitle}
          subtitle={subtitle}
          onSelect={onSelectPrompt}
        />
      ) : (
        <div className="flex flex-col gap-3">
          {messages.map((m) => (
            <AssistantMessage key={m.id} message={m} />
          ))}
          {statusPhase && statusPhase !== "responding" ? (
            <p className="text-xs text-muted-foreground">
              {statusPhase === "tools" ? "Working…" : "Starting…"}
            </p>
          ) : null}
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
