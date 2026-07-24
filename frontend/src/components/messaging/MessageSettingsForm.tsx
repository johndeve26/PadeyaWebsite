"use client";

import { useEffect, useState } from "react";

import {
  Alert,
  Button,
  Card,
  EmptyState,
  SkeletonLoader,
  Switch,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchMessageSettings,
  unblockMessagingUser,
  updateMessageSettings,
} from "@/lib/messaging-api";
import type { MessageSettings } from "@/lib/types/messaging";
import { formatDate } from "@/lib/format";

type FanBoolKey =
  | "allow_messages_from_hosts_i_follow"
  | "allow_messages_from_hosts_i_attended"
  | "allow_messages_from_public"
  | "message_requests_enabled";

type HostBoolKey =
  | "allow_messages_from_followers"
  | "allow_messages_from_ticket_buyers"
  | "allow_messages_from_public_host"
  | "allow_event_inquiries"
  | "auto_reply_enabled";

const FAN_TOGGLES: { key: FanBoolKey; label: string; hint: string }[] = [
  {
    key: "allow_messages_from_hosts_i_follow",
    label: "Hosts I follow",
    hint: "Hosts you follow on Pàdéyá can message you.",
  },
  {
    key: "allow_messages_from_hosts_i_attended",
    label: "Hosts I attended",
    hint: "Hosts from tickets or check-ins can message you.",
  },
  {
    key: "allow_messages_from_public",
    label: "Public messaging",
    hint: "Allow cold messages from hosts without a relationship (off for demo fans).",
  },
  {
    key: "message_requests_enabled",
    label: "Message requests",
    hint: "When on, weak-relationship messages can arrive as requests.",
  },
];

const HOST_TOGGLES: { key: HostBoolKey; label: string; hint: string }[] = [
  {
    key: "allow_messages_from_followers",
    label: "Followers",
    hint: "Fans who follow your Legacy Page can message you.",
  },
  {
    key: "allow_messages_from_ticket_buyers",
    label: "Ticket buyers & checked-in attendees",
    hint: "Fans with a ticket or check-in can message you.",
  },
  {
    key: "allow_messages_from_public_host",
    label: "Public messages",
    hint: "Allow cold public contact (usually as a message request).",
  },
  {
    key: "allow_event_inquiries",
    label: "Event inquiries",
    hint: "Fans can ask about your events from event pages.",
  },
  {
    key: "auto_reply_enabled",
    label: "Auto-reply",
    hint: "Send a safe automatic reply on new active conversations.",
  },
];

export function MessageSettingsForm({ mode }: { mode: "fan" | "host" }) {
  const toast = useToast();
  const [settings, setSettings] = useState<MessageSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function reload() {
    const data = await fetchMessageSettings();
    setSettings(data);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchMessageSettings();
        if (!active) return;
        setSettings(data);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(err instanceof ApiError ? err.detail : "Failed to load settings");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function patch(partial: Partial<Omit<MessageSettings, "blocked_users">>) {
    if (!settings) return;
    setSaving(true);
    try {
      const next = await updateMessageSettings(partial);
      setSettings(next);
      toast.push({ tone: "success", title: "Settings saved" });
    } catch (err) {
      toast.push({
        tone: "danger",
        title: err instanceof ApiError ? err.detail : "Could not save",
      });
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <SkeletonLoader lines={8} />;
  if (error) {
    return (
      <Alert tone="danger" title="Could not load">
        {error}
      </Alert>
    );
  }
  if (!settings) return null;

  const toggles = mode === "fan" ? FAN_TOGGLES : HOST_TOGGLES;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card className="space-y-5">
        <div>
          <h2 className="text-lg font-extrabold text-foreground">Who can message you</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Privacy-first controls. Emails and phone numbers are never required.
          </p>
        </div>
        <div className="space-y-4">
          {toggles.map((t) => (
            <Switch
              key={t.key}
              id={t.key}
              label={t.label}
              description={t.hint}
              checked={Boolean(settings[t.key as keyof MessageSettings])}
              disabled={saving}
              onCheckedChange={(checked) => void patch({ [t.key]: checked })}
            />
          ))}
        </div>
        {mode === "host" && settings.auto_reply_enabled ? (
          <div className="space-y-2 border-t border-border pt-4">
            <label className="block text-sm font-semibold text-foreground">
              Auto-reply message
            </label>
            <Textarea
              value={settings.auto_reply_message || ""}
              rows={3}
              disabled={saving}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  auto_reply_message: e.target.value.slice(0, 500),
                })
              }
              placeholder="Thanks for messaging on Pàdéyá…"
            />
            <Button
              size="sm"
              disabled={saving}
              onClick={() =>
                void patch({
                  auto_reply_message: settings.auto_reply_message,
                  auto_reply_enabled: true,
                })
              }
            >
              Save auto-reply
            </Button>
          </div>
        ) : null}
      </Card>

      <Card className="space-y-4">
        <div>
          <h2 className="text-lg font-extrabold text-foreground">Blocked users</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Blocked accounts cannot message you. Display names only — no private contact data.
          </p>
        </div>
        {settings.blocked_users.length === 0 ? (
          <EmptyState
            title="No blocked users"
            description="When you block someone from a conversation, they appear here."
          />
        ) : (
          <ul className="space-y-3">
            {settings.blocked_users.map((b) => (
              <li
                key={b.user_id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-md)] border border-border bg-surface-muted/40 px-3 py-3 dark:bg-surface-elevated/40"
              >
                <div className="min-w-0 space-y-0.5">
                  <p className="font-semibold text-foreground">{b.display_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {b.role}
                    {b.username ? ` · @${b.username}` : ""}
                    {b.reason ? ` · ${b.reason}` : ""}
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    {formatDate(b.created_at)}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={saving}
                  onClick={() =>
                    void unblockMessagingUser(b.user_id, mode === "host")
                      .then(() => reload())
                      .then(() =>
                        toast.push({ tone: "success", title: "User unblocked" }),
                      )
                      .catch((err) =>
                        toast.push({
                          tone: "danger",
                          title:
                            err instanceof ApiError ? err.detail : "Unblock failed",
                        }),
                      )
                  }
                >
                  Unblock
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
