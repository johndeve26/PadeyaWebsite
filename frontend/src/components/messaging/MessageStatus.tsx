"use client";

import { cn } from "@/lib/cn";
import { formatOwnDeliveryStatus } from "@/lib/messaging/message-status";
import type { MessageItem } from "@/lib/types/messaging";

/** Edited badge + own-message delivery (Sent / Delivered / Read / Failed). */
export function MessageStatus({
  message,
  peerReadAt = null,
  className,
}: {
  message: MessageItem;
  peerReadAt?: string | null;
  className?: string;
}) {
  const bits: string[] = [];
  if (message.edited_at) bits.push("Edited");
  if (message.is_mine) {
    const delivery = formatOwnDeliveryStatus({
      isMine: true,
      status: message.status,
      createdAt: message.created_at,
      editedAt: message.edited_at,
      peerReadAt,
      clientFailed: message.client_failed,
    });
    if (delivery) bits.push(delivery);
  }
  if (!bits.length) return null;

  return (
    <span className={cn("text-[10px] font-semibold", className)}>
      {bits.join(" · ")}
    </span>
  );
}
