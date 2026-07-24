"use client";

import { cn } from "@/lib/cn";
import { formatMessageSentAt } from "@/lib/format-message-time";

/** Clock label under a message bubble. */
export function MessageTimestamp({
  createdAt,
  className,
  /** @deprecated Timestamps are always visible; kept for call-site compatibility. */
  alwaysVisible: _alwaysVisible = false,
}: {
  createdAt?: string | null;
  className?: string;
  alwaysVisible?: boolean;
}) {
  const label = formatMessageSentAt(createdAt);
  if (!label) return null;

  return (
    <time
      dateTime={createdAt || undefined}
      className={cn("text-[10px] font-semibold", className)}
    >
      {label}
    </time>
  );
}
