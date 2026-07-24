"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, Card, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAdminFanConnectSettings,
  updateAdminFanConnectSettings,
} from "@/lib/fan-connect-api";

export default function AdminFanConnectSettingsPage() {
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchAdminFanConnectSettings();
        if (!active) return;
        setDays(data.decline_cooldown_days_default);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError ? err.detail : "Could not load settings.",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function save() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const data = await updateAdminFanConnectSettings({
        decline_cooldown_days_default: days,
      });
      setDays(data.decline_cooldown_days_default);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Fan Connect settings"
      description="Platform defaults for opt-in fan↔fan Connect."
      actions={
        <Link href="/admin/fan-connect">
          <Button variant="secondary">Back to Fan Connect</Button>
        </Link>
      }
    >
      {loading ? <SkeletonLoader className="h-40" /> : null}
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {saved ? (
        <Alert tone="success">Settings saved.</Alert>
      ) : null}
      {!loading ? (
        <Card className="max-w-lg space-y-4 p-6">
          <div>
            <label
              htmlFor="fc-decline-default"
              className="text-sm font-semibold text-foreground"
            >
              Default decline cooldown (days)
            </label>
            <p className="mt-1 text-sm text-muted">
              When a user declines a connect request, the requester cannot send
              another request to that same person until this cooldown ends. The
              person who declined can still send a request back at any time.
            </p>
            <input
              id="fc-decline-default"
              type="number"
              min={0}
              max={365}
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="mt-3 w-full rounded-[var(--radius-md)] border border-border bg-background px-3 py-2 text-sm"
            />
          </div>
          <Button disabled={saving} onClick={() => void save()}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </Card>
      ) : null}
    </DashboardShell>
  );
}
