"use client";

import { useEffect, useId, useRef } from "react";

import { AssistantComposer } from "@/components/assistant/AssistantComposer";
import { AssistantHeader } from "@/components/assistant/AssistantHeader";
import { AssistantMessageList } from "@/components/assistant/AssistantMessageList";
import { cn } from "@/lib/cn";
import type {
  AssistantChatMessage,
  AssistantSuggestedPrompt,
} from "@/lib/types/assistant";

function trapFocus(container: HTMLElement, e: KeyboardEvent) {
  if (e.key !== "Tab") return;
  const focusable = container.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
  );
  const list = Array.from(focusable).filter(
    (el) => !el.hasAttribute("disabled") && el.offsetParent !== null,
  );
  if (list.length === 0) return;
  const first = list[0];
  const last = list[list.length - 1];
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault();
    first.focus();
  }
}

export function AssistantPanel({
  title,
  subtitle,
  online,
  messages,
  role,
  streaming,
  statusPhase,
  onSend,
  onStop,
  onNewChat,
  onClose,
  mobileFullscreen,
}: {
  title: string;
  subtitle: string;
  online: boolean;
  messages: AssistantChatMessage[];
  role: string | null;
  streaming: boolean;
  statusPhase?: string | null;
  onSend: (message: string) => void;
  onStop: () => void;
  onNewChat: () => void;
  onClose: () => void;
  mobileFullscreen?: boolean;
}) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        return;
      }
      if (mobileFullscreen) trapFocus(panel, e);
    };

    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    if (mobileFullscreen) {
      document.body.style.overflow = "hidden";
    }

    // Focus first focusable control for a11y
    const focusable = panel.querySelector<HTMLElement>(
      'button:not([disabled]), textarea:not([disabled])',
    );
    focusable?.focus();

    return () => {
      document.removeEventListener("keydown", onKey);
      if (mobileFullscreen) {
        document.body.style.overflow = prevOverflow;
      }
    };
  }, [mobileFullscreen, onClose]);

  function onSelectPrompt(prompt: AssistantSuggestedPrompt) {
    onSend(prompt.message);
  }

  return (
    <div
      ref={panelRef}
      role={mobileFullscreen ? "dialog" : "complementary"}
      aria-modal={mobileFullscreen ? true : undefined}
      aria-labelledby={titleId}
      className={cn(
        "flex flex-col overflow-hidden border border-border bg-popover text-popover-foreground shadow-[var(--shadow-strong)]",
        "motion-safe:transition-opacity motion-safe:duration-200 motion-reduce:transition-none",
        mobileFullscreen
          ? "fixed inset-0 z-[90] rounded-none pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]"
          : "h-[min(640px,calc(100dvh-6rem))] w-[min(100vw-1.5rem,24rem)] rounded-[var(--radius-xl)]",
      )}
    >
      <span id={titleId} className="sr-only">
        {title}
      </span>
      <AssistantHeader
        title={title}
        subtitle={subtitle}
        online={online}
        onNewChat={onNewChat}
        onClose={onClose}
      />
      <AssistantMessageList
        messages={messages}
        role={role}
        productTitle={title}
        subtitle={subtitle}
        statusPhase={statusPhase}
        onSelectPrompt={onSelectPrompt}
      />
      <AssistantComposer
        streaming={streaming}
        onSend={onSend}
        onStop={onStop}
      />
    </div>
  );
}
