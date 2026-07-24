"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  Select,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAdminSupportSettings,
  updateAdminSupportSettings,
} from "@/lib/support-api";
import type { SupportSettings } from "@/lib/types/support";

export default function AdminSupportSettingsPage() {
  const toast = useToast();
  const [settings, setSettings] = useState<SupportSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setSettings(await fetchAdminSupportSettings());
      setError(null);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to load settings",
      );
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate settings
    void load();
  }, [load]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!settings) return;
    setBusy(true);
    try {
      const updated = await updateAdminSupportSettings(settings);
      setSettings(updated);
      toast.push({ tone: "success", title: "Settings saved" });
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Save failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Support"
      title="Support settings"
      description="Configure auto-assign, urgent alerts, and the public contact form."
      actions={
        <Link href="/admin/support">
          <Button variant="secondary">Back to queue</Button>
        </Link>
      }
    >
      {error ? (
        <Alert tone="danger" title="Settings unavailable">
          {error}
        </Alert>
      ) : null}

      {!settings && !error ? <SkeletonLoader lines={5} /> : null}

      {settings ? (
        <Card className="max-w-xl space-y-5 p-5 sm:p-6">
          <form onSubmit={onSubmit} className="space-y-5">
            <label className="flex items-start gap-3 text-sm">
              <input
                type="checkbox"
                className="mt-1 size-4 rounded border-border"
                checked={settings.auto_assign_enabled}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    auto_assign_enabled: e.target.checked,
                  })
                }
              />
              <span>
                <span className="font-bold text-foreground">Auto-assign</span>
                <span className="mt-0.5 block text-muted-foreground">
                  Automatically assign new tickets when agents are available.
                </span>
              </span>
            </label>

            <label className="flex items-start gap-3 text-sm">
              <input
                type="checkbox"
                className="mt-1 size-4 rounded border-border"
                checked={settings.notify_on_urgent}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    notify_on_urgent: e.target.checked,
                  })
                }
              />
              <span>
                <span className="font-bold text-foreground">
                  Notify on urgent
                </span>
                <span className="mt-0.5 block text-muted-foreground">
                  Alert the support team when an urgent ticket is opened.
                </span>
              </span>
            </label>

            <label className="flex items-start gap-3 text-sm">
              <input
                type="checkbox"
                className="mt-1 size-4 rounded border-border"
                checked={settings.public_form_enabled}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    public_form_enabled: e.target.checked,
                  })
                }
              />
              <span>
                <span className="font-bold text-foreground">
                  Public contact form
                </span>
                <span className="mt-0.5 block text-muted-foreground">
                  Allow visitors to submit tickets without signing in.
                </span>
              </span>
            </label>

            <Select
              label="Default priority"
              value={settings.default_priority}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  default_priority: e.target.value,
                })
              }
            >
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </Select>

            <Button type="submit" disabled={busy}>
              {busy ? "Saving…" : "Save settings"}
            </Button>
          </form>
        </Card>
      ) : null}
    </DashboardShell>
  );
}
