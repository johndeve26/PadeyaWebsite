"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { useAuth } from "@/components/auth/AuthProvider";
import { Alert, Button, Card } from "@/components/ui";
import { PushHomeScreenHint } from "@/components/notifications/PushHomeScreenHint";
import {
  dismissPushPrompt,
  usePushNotifications,
  wasPushPromptDismissed,
} from "@/hooks/usePushNotifications";
import { PUSH_DENIED_COPY } from "@/lib/push-device";

type Props = {
  /**
   * Where the calm prompt is shown. Never requests browser permission on mount.
   * Prefer settings / notifications — not the global first paint.
   */
  context?: "settings" | "notifications" | "action";
  className?: string;
};

/**
 * Calm in-app opt-in for browser push.
 * Browser Notification.requestPermission runs only after “Enable notifications”.
 */
export function PushPermissionPrompt({
  context = "notifications",
  className,
}: Props) {
  const { user } = useAuth();
  const push = usePushNotifications();
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    queueMicrotask(() => {
      setDismissed(wasPushPromptDismissed());
    });
  }, []);

  if (!user) return null;
  if (push.subscribed) return null;
  if (dismissed && context !== "settings") return null;

  const needsHomeScreen = push.device.needsHomeScreenForPush;

  // Never show the Enable / browser permission prompt when push is unsupported.
  // Settings page owns unsupported + Home Screen helpers via PushSettingsPanel.
  if (!push.supported) {
    if (context === "settings") return null;
    if (needsHomeScreen) {
      return <PushHomeScreenHint show className={className} />;
    }
    return null;
  }

  if (!push.canOfferOptIn && push.permission !== "denied") return null;

  if (push.permission === "denied") {
    return (
      <Alert tone="warning" title="Notifications blocked" className={className}>
        {PUSH_DENIED_COPY}
      </Alert>
    );
  }

  if (!push.adminEnabled) return null;

  return (
    <Card className={`space-y-3 p-4 ${className ?? ""}`}>
      <div className="space-y-1">
        <h3 className="font-bold tracking-tight">Stay updated on Pàdéyá</h3>
        <p className="text-sm text-muted-foreground">
          Optional browser alerts when you’re away — tickets, merch pickup, and
          messages (never private chat bodies). We’ll only ask your browser after
          you choose to enable.
        </p>
      </div>
      {needsHomeScreen && context !== "settings" ? (
        <PushHomeScreenHint show />
      ) : null}
      {push.error ? (
        <Alert tone="danger" title="Could not enable">
          {push.error}
        </Alert>
      ) : null}
      {push.note ? (
        <Alert tone="success" title="Updated">
          {push.note}
        </Alert>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          disabled={push.busy || !push.supported}
          onClick={() => void push.enable()}
        >
          {push.busy ? "Enabling…" : "Enable notifications"}
        </Button>
        {context === "notifications" || context === "action" ? (
          <Button
            size="sm"
            variant="ghost"
            disabled={push.busy}
            onClick={() => {
              dismissPushPrompt();
              setDismissed(true);
            }}
          >
            Not now
          </Button>
        ) : null}
        {context !== "settings" ? (
          <Link href="/dashboard/settings/notifications">
            <Button size="sm" variant="secondary">
              Preferences
            </Button>
          </Link>
        ) : null}
      </div>
    </Card>
  );
}
