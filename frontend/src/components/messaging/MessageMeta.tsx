"use client";

import { MessageStatus } from "@/components/messaging/MessageStatus";
import { MessageTimestamp } from "@/components/messaging/MessageTimestamp";
import { cn } from "@/lib/cn";
import type { MessageItem } from "@/lib/types/messaging";

/** Clock + edited / delivery chips under a bubble. */
export function MessageMeta({
  message,
  peerReadAt = null,
  mineTone = false,
  alwaysShowTimestamp = false,
}: {
  message: MessageItem;
  peerReadAt?: string | null;
  /** Primary-colored bubble (own message). */
  mineTone?: boolean;
  alwaysShowTimestamp?: boolean;
}) {
  const failed =
    mineTone && (message.client_failed || message.status === "failed");
  const tone = mineTone
    ? failed
      ? "text-primary-foreground"
      : "text-primary-foreground/70"
    : "text-muted-foreground";

  return (
    <div className={cn("flex flex-wrap items-center gap-x-1.5 gap-y-0.5", tone)}>
      <MessageTimestamp
        createdAt={message.created_at}
        alwaysVisible={alwaysShowTimestamp}
        className={tone}
      />
      <MessageStatus
        message={message}
        peerReadAt={peerReadAt}
        className={tone}
      />
    </div>
  );
}
