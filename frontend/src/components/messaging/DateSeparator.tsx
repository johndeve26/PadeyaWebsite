"use client";

import { formatMessageDaySeparator } from "@/lib/format-message-time";

/** Day label between message groups (Today / Yesterday / weekday date). */
export function DateSeparator({
  createdAt,
}: {
  createdAt?: string | null;
}) {
  const label = formatMessageDaySeparator(createdAt);
  if (!label) return null;

  return (
    <p className="py-2 text-center text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
      {label}
    </p>
  );
}
