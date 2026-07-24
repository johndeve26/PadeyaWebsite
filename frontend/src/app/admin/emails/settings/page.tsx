"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, Card } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAdminEmailNotificationSettings,
  updateAdminEmailNotificationSettings,
  type AdminEmailNotificationSettings,
} from "@/lib/email-api";

export default function AdminEmailsSettingsHubPage() {
  const [settings, setSettings] = useState<AdminEmailNotificationSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void fetchAdminEmailNotificationSettings()
      .then((row) => {
        if (active) setSettings(row);
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load settings");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function toggle(field: "master_enabled" | "digest_enabled") {
    if (!settings) return;
    try {
      const next = await updateAdminEmailNotificationSettings({
        [field]: !settings[field],
      });
      setSettings(next);
      setNote("Settings updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Email settings"
      description="SMTP provider, platform admin notification emails, and template delivery."
      actions={
        <Link href="/admin/emails/templates">
          <Button size="sm">Platform templates</Button>
        </Link>
      }
    >
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Saved">
          {note}
        </Alert>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <Card padded className="space-y-3">
          <h2 className="text-lg font-extrabold">SMTP & outbox</h2>
          <p className="text-sm text-muted-foreground">
            Provider credentials, test send, and transactional outbox drain.
          </p>
          <Link href="/admin/email/settings">
            <Button variant="secondary">Open SMTP settings</Button>
          </Link>
          <Link href="/admin/emails" className="block">
            <Button variant="ghost" className="w-full sm:w-auto">
              View outbox
            </Button>
          </Link>
        </Card>

        <Card padded className="space-y-3">
          <h2 className="text-lg font-extrabold">Admin platform notifications</h2>
          <p className="text-sm text-muted-foreground">
            Master switch for admin-only platform emails (reports, sales signals, support).
            Fan and host templates are unchanged.
          </p>
          {settings ? (
            <div className="space-y-2 text-sm">
              <label className="flex items-center gap-2 font-semibold">
                <input
                  type="checkbox"
                  checked={settings.master_enabled}
                  onChange={() => void toggle("master_enabled")}
                />
                Admin emails enabled
              </label>
              <label className="flex items-center gap-2 font-semibold">
                <input
                  type="checkbox"
                  checked={settings.digest_enabled}
                  onChange={() => void toggle("digest_enabled")}
                />
                Digest mode (batch low-priority templates)
              </label>
              <p className="text-xs text-muted-foreground">
                Digest hour (UTC): {settings.digest_hour_utc}:00
              </p>
            </div>
          ) : null}
        </Card>
      </div>
    </DashboardShell>
  );
}
