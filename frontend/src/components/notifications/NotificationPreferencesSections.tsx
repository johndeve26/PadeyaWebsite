"use client";

import { useEffect, useState } from "react";

import { PushSettingsPanel } from "@/components/notifications/PushSettingsPanel";
import { Alert, Button, Card, SectionHeader, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchEmailPreferences,
  updateEmailPreferences,
  type EmailPreferences,
} from "@/lib/email-api";
import {
  fetchPushPreferences,
  updatePushPreferences,
  type PushPreferences,
} from "@/lib/notifications-api";
import {
  playCheckInScanSound,
  playInAppNotificationSound,
  readUiSoundPreferences,
  unlockUiSounds,
  writeUiSoundPreferences,
  type UiSoundPreferences,
} from "@/lib/ui-sounds";

const EMAIL_TOGGLES: {
  key: keyof EmailPreferences;
  label: string;
  hint: string;
  locked?: boolean;
}[] = [
  {
    key: "email_security",
    label: "Security emails",
    hint: "Password and account security — always on.",
    locked: true,
  },
  {
    key: "email_ticket_updates",
    label: "Ticket updates",
    hint: "Event changes, cancellations, refunds. Purchase confirmations still send.",
  },
  {
    key: "email_merch_updates",
    label: "Merch updates",
    hint: "Pickup, shipping, and refunds. Paid order confirmations still send.",
  },
  {
    key: "email_event_reminders",
    label: "Event reminders",
    hint: "Reminders before events you hold tickets for.",
  },
  {
    key: "email_messages",
    label: "Message emails",
    hint: "New messages when you’re away (no chat contents in email).",
  },
  {
    key: "email_fan_connect",
    label: "Fan Connect",
    hint: "Connection requests and acceptances.",
  },
  {
    key: "email_sponsor_updates",
    label: "Sponsor updates",
    hint: "Inquiry confirmations and status changes.",
  },
  {
    key: "email_host_activity",
    label: "Host activity",
    hint: "Sales, reviews, and sponsor inquiries (hosts).",
  },
  {
    key: "email_marketing",
    label: "Marketing & post-event drops",
    hint: "Optional drops and cart reminders. On by default — turn off anytime.",
  },
];

const PUSH_TOGGLES: {
  key: keyof PushPreferences;
  label: string;
  hint: string;
  locked?: boolean;
}[] = [
  {
    key: "push_enabled",
    label: "Browser push master switch",
    hint: "On by default. Still needs this device subscribed for any push alerts.",
  },
  {
    key: "push_security",
    label: "Security push",
    hint: "Account security alerts — always on when push is enabled. Bypasses marketing opt-out.",
    locked: true,
  },
  {
    key: "push_ticket_updates",
    label: "Ticket push",
    hint: "Verified ticket updates. You can turn off; purchase email still sends.",
  },
  {
    key: "push_merch_updates",
    label: "Merch push",
    hint: "Pickup and shipping. You can turn off; paid order email still sends.",
  },
  {
    key: "push_event_reminders",
    label: "Event reminder push",
    hint: "Reminders before events you hold tickets for.",
  },
  {
    key: "push_messages",
    label: "Message push",
    hint: "New messages when you’re away. Generic copy only — never full chat text.",
  },
  {
    key: "push_message_previews",
    label: "Message sender preview",
    hint: "Show “Name sent you a message.” Still never includes message text.",
  },
  {
    key: "push_fan_connect",
    label: "Fan Connect push",
    hint: "Connection requests and acceptances.",
  },
  {
    key: "push_sponsor_updates",
    label: "Sponsor push",
    hint: "Inquiry status updates.",
  },
  {
    key: "push_host_activity",
    label: "Host activity push",
    hint: "Sales and host operational alerts.",
  },
  {
    key: "push_reviews",
    label: "Review push",
    hint: "New reviews and review replies.",
  },
  {
    key: "push_marketing",
    label: "Marketing push",
    hint: "Drops and promos. On by default — turn off anytime.",
  },
];

/**
 * Email preferences + browser push device panel + push category toggles.
 * Shared by Account Settings and the notifications deep-link page.
 */
export function NotificationPreferencesSections() {
  const toast = useToast();
  const [prefs, setPrefs] = useState<EmailPreferences | null>(null);
  const [pushPrefs, setPushPrefs] = useState<PushPreferences | null>(null);
  const [uiSounds, setUiSounds] = useState<UiSoundPreferences | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setUiSounds(readUiSoundPreferences());
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [emailData, pushData] = await Promise.all([
          fetchEmailPreferences(),
          fetchPushPreferences(),
        ]);
        if (active) {
          setPrefs(emailData);
          setPushPrefs(pushData);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load preferences",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  function toggleUiSound(key: keyof UiSoundPreferences) {
    if (!uiSounds) return;
    const next = writeUiSoundPreferences({ [key]: !uiSounds[key] });
    setUiSounds(next);
    void unlockUiSounds().then(() => {
      if (key === "notifications") playInAppNotificationSound();
      else playCheckInScanSound("valid");
    });
  }

  async function toggle(key: keyof EmailPreferences) {
    if (!prefs || key === "email_security") return;
    setBusy(true);
    setError(null);
    try {
      const next = await updateEmailPreferences({ [key]: !prefs[key] });
      setPrefs(next);
      toast.push({ tone: "success", title: "Preferences saved" });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not update preferences",
      );
    } finally {
      setBusy(false);
    }
  }

  async function togglePush(key: keyof PushPreferences) {
    if (!pushPrefs || key === "push_security") return;
    setBusy(true);
    setError(null);
    try {
      const next = await updatePushPreferences({ [key]: !pushPrefs[key] });
      setPushPrefs(next);
      toast.push({ tone: "success", title: "Push preferences saved" });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not update push preferences",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}

      <div className="max-w-2xl min-w-0">
        <PushSettingsPanel />
      </div>

      <Card className="max-w-2xl min-w-0 space-y-5 overflow-hidden">
        <SectionHeader
          eyebrow="In-app"
          title="Sound alerts"
          description="Plays in this browser when you get a notification toast or scan a ticket at the door. Tap anywhere on the site once if audio is silent."
        />
        {!uiSounds ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : (
          <ul className="divide-y divide-border">
            <li className="flex min-w-0 flex-wrap items-center justify-between gap-3 py-3">
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-foreground">
                  Notification sounds
                </p>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  Chime when an in-app alert appears (messages, tickets, host
                  activity, and similar).
                </p>
              </div>
              <Button
                size="sm"
                className="shrink-0"
                variant={uiSounds.notifications ? "secondary" : "ghost"}
                aria-pressed={uiSounds.notifications}
                onClick={() => toggleUiSound("notifications")}
              >
                {uiSounds.notifications ? "On" : "Off"}
              </Button>
            </li>
            <li className="flex min-w-0 flex-wrap items-center justify-between gap-3 py-3">
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-foreground">
                  Check-in scan sounds
                </p>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  Different tones for valid, duplicate, and invalid scans on the
                  door scanner.
                </p>
              </div>
              <Button
                size="sm"
                className="shrink-0"
                variant={uiSounds.scan ? "secondary" : "ghost"}
                aria-pressed={uiSounds.scan}
                onClick={() => toggleUiSound("scan")}
              >
                {uiSounds.scan ? "On" : "Off"}
              </Button>
            </li>
          </ul>
        )}
      </Card>

      <Card className="max-w-2xl min-w-0 space-y-5 overflow-hidden">
        <SectionHeader
          eyebrow="Email"
          title="Email notifications"
          description="Purchase and security emails stay on. Everything else is optional."
        />
        {!prefs ? (
          <p className="text-sm text-muted-foreground">Loading preferences…</p>
        ) : (
          <ul className="divide-y divide-border">
            {EMAIL_TOGGLES.map((item) => {
              const on = Boolean(prefs[item.key]);
              return (
                <li
                  key={item.key}
                  className="flex min-w-0 flex-wrap items-center justify-between gap-3 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-foreground">{item.label}</p>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      {item.hint}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    className="shrink-0"
                    variant={on ? "secondary" : "ghost"}
                    disabled={busy || item.locked}
                    aria-pressed={on}
                    onClick={() => void toggle(item.key)}
                  >
                    {item.locked ? "Always on" : on ? "On" : "Off"}
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      <Card className="max-w-2xl min-w-0 space-y-5 overflow-hidden">
        <SectionHeader
          eyebrow="Push"
          title="Push categories"
          description="Applies after this device is enabled. Master switch off blocks all push."
        />
        {!pushPrefs ? (
          <p className="text-sm text-muted-foreground">
            Loading push preferences…
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {PUSH_TOGGLES.map((item) => {
              const on = Boolean(pushPrefs[item.key]);
              return (
                <li
                  key={item.key}
                  className="flex min-w-0 flex-wrap items-center justify-between gap-3 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-foreground">{item.label}</p>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      {item.hint}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    className="shrink-0"
                    variant={on ? "secondary" : "ghost"}
                    disabled={busy || item.locked}
                    aria-pressed={on}
                    onClick={() => void togglePush(item.key)}
                  >
                    {item.locked ? "Always on" : on ? "On" : "Off"}
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
}
