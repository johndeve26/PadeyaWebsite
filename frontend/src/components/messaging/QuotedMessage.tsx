"use client";

import { cn } from "@/lib/cn";
import type { MessageItem } from "@/lib/types/messaging";

/** In-bubble quote for `reply_to` — tap scrolls to the original when available. */
export function QuotedMessage({
  reply,
  mine = false,
  onTap,
}: {
  reply: NonNullable<MessageItem["reply_to"]>;
  mine?: boolean;
  onTap?: (messageId: string, unavailable?: boolean) => void;
}) {
  const unavailable = Boolean(reply.reply_is_unavailable);
  const preview =
    reply.reply_body_preview ||
    reply.reply_attachment_preview ||
    (unavailable ? "Original message unavailable" : "");

  return (
    <button
      type="button"
      disabled={unavailable}
      className={cn(
        "w-full rounded-[var(--radius-sm)] border-l-2 px-2 py-1 text-left text-xs",
        mine
          ? "border-primary-foreground/50 bg-primary-foreground/10"
          : "border-primary/50 bg-background/40",
        unavailable ? "cursor-default opacity-80" : null,
      )}
      onClick={() => onTap?.(reply.reply_message_id, unavailable)}
    >
      {!unavailable && reply.reply_author_display_name ? (
        <p className="font-bold opacity-80">{reply.reply_author_display_name}</p>
      ) : null}
      <p className="line-clamp-2 opacity-70">{preview}</p>
      {reply.reply_attachment_preview &&
      reply.reply_body_preview &&
      !unavailable ? (
        <p className="mt-0.5 truncate opacity-60">
          {reply.reply_attachment_preview}
        </p>
      ) : null}
    </button>
  );
}
