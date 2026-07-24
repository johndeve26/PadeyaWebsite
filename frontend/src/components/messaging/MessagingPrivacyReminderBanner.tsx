"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  dismissMessagingPrivacyReminderUntilMidnight,
  isMessagingPrivacyReminderDismissed,
  msUntilMessagingPrivacyReminderReturns,
} from "@/lib/messaging/privacy-reminder-dismiss";

const DEFAULT_COPY =
  "Keep this conversation on Pàdéyá. Do not share phone numbers, emails, WhatsApp, bank details, or payment links. Report fraud or anything suspicious from this conversation.";

export function MessagingPrivacyReminderBanner({
  text,
  className,
}: {
  text?: string | null;
  className?: string;
}) {
  const copy = (text || DEFAULT_COPY).trim();
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    setVisible(!isMessagingPrivacyReminderDismissed());
  }, []);

  const scheduleReshow = useCallback((delayMs: number) => {
    if (delayMs <= 0 || delayMs > 86_400_000) return;
    const t = window.setTimeout(() => setVisible(true), delayMs);
    return () => window.clearTimeout(t);
  }, []);

  useEffect(() => {
    if (visible) return;
    const delay = msUntilMessagingPrivacyReminderReturns();
    return scheduleReshow(delay);
  }, [visible, scheduleReshow]);

  const dismiss = () => {
    dismissMessagingPrivacyReminderUntilMidnight();
    setVisible(false);
  };

  if (!visible || !copy) return null;

  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-[var(--radius-md)] bg-surface-muted/40 px-2 py-1.5 dark:bg-surface-inset/40",
        className,
      )}
      role="note"
    >
      <p className="min-w-0 flex-1 text-xs leading-relaxed text-muted-foreground">
        {copy}
      </p>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-8 shrink-0 px-2 text-xs font-bold text-muted-foreground"
        aria-label="Dismiss safety reminder until midnight"
        onClick={dismiss}
      >
        Dismiss
      </Button>
    </div>
  );
}
