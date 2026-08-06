"use client";

import Link from "next/link";

import { AssistantMarkdown } from "@/components/assistant/AssistantMarkdown";
import { CitationList } from "@/components/assistant/cards/CitationList";
import { ConfirmationCard } from "@/components/assistant/cards/ConfirmationCard";
import { EventCard } from "@/components/assistant/cards/EventCard";
import { HostCard } from "@/components/assistant/cards/HostCard";
import { RouteCard } from "@/components/assistant/cards/RouteCard";
import { SupportCard } from "@/components/assistant/cards/SupportCard";
import { cn } from "@/lib/cn";
import type {
  AssistantAction,
  AssistantCard,
  AssistantChatMessage,
} from "@/lib/types/assistant";

function CardRenderer({
  card,
  confirmationId,
}: {
  card: AssistantCard;
  confirmationId?: string | null;
}) {
  const type = (card.type || "").toLowerCase();
  if (type === "event") return <EventCard card={card} />;
  if (type === "host") return <HostCard card={card} />;
  if (type === "route" || type === "navigation") return <RouteCard card={card} />;
  if (type === "confirmation" || type === "confirm") {
    return (
      <ConfirmationCard card={card} confirmationId={confirmationId} />
    );
  }
  if (type === "support") return <SupportCard card={card} />;
  // Generic fallback as route-like card
  return <RouteCard card={card} />;
}

function ActionChips({ actions }: { actions: AssistantAction[] }) {
  if (!actions.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {actions.map((a, i) => {
        const href = a.url || null;
        const key = `${a.label}-${i}`;
        const className =
          "inline-flex items-center rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold text-foreground transition-colors hover:border-primary/40 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring";
        if (href?.startsWith("/")) {
          return (
            <Link key={key} href={href} className={className}>
              {a.label}
            </Link>
          );
        }
        if (href) {
          return (
            <a
              key={key}
              href={href}
              className={className}
              rel="noopener noreferrer"
              target="_blank"
            >
              {a.label}
            </a>
          );
        }
        return (
          <span key={key} className={cn(className, "opacity-80")}>
            {a.label}
          </span>
        );
      })}
    </div>
  );
}

export function AssistantMessage({ message }: { message: AssistantChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex w-full",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "min-w-0 max-w-[min(100%,22rem)] space-y-2 rounded-[var(--radius-lg)] px-3.5 py-2.5",
          isUser
            ? "bg-ink text-paper"
            : message.error
              ? "border border-danger/30 bg-surface-muted text-foreground dark:bg-surface-elevated"
              : "bg-surface-muted text-foreground dark:bg-surface-elevated",
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
            {message.content}
          </p>
        ) : (
          <>
            {message.content ? (
              <AssistantMarkdown
                content={message.content}
                className={isUser ? "text-paper" : undefined}
              />
            ) : message.streaming ? (
              <p className="text-sm text-muted-foreground">Thinking…</p>
            ) : null}
            {message.cards?.length ? (
              <div className="space-y-2">
                {message.cards.map((card, i) => (
                  <CardRenderer
                    key={`${card.type}-${card.title}-${i}`}
                    card={card}
                    confirmationId={message.confirmationId}
                  />
                ))}
              </div>
            ) : null}
            {message.actions?.length ? (
              <ActionChips actions={message.actions} />
            ) : null}
            {message.citations?.length ? (
              <CitationList citations={message.citations} />
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
