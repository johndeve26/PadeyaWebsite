"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { PushSettingsPanel } from "@/components/notifications/PushSettingsPanel";
import {
  Alert,
  Badge,
  Button,
  Card,
  Input,
  Select,
  Switch,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  disableAdminPush,
  fetchAdminPushDeliveries,
  fetchAdminPushSettings,
  lookupAdminPushSubscriptions,
  testAdminPush,
  testAdminPushToUser,
  updateAdminPushSettings,
  type AdminPushSubscriptionLookup,
  type PushDeliveryEvent,
  type PushProviderMode,
  type PushProviderSettings,
} from "@/lib/notifications-api";

function AdminPushSettingsPageInner() {
  const [settings, setSettings] = useState<PushProviderSettings | null>(null);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [provider, setProvider] = useState<PushProviderMode>("log");
  const [subject, setSubject] = useState("mailto:support@padeya.com");
  const [publicKey, setPublicKey] = useState("");
  const [privateKey, setPrivateKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [lookingUp, setLookingUp] = useState(false);
  const [testTargetEmail, setTestTargetEmail] = useState("");
  const [testTargetUserId, setTestTargetUserId] = useState("");
  const [lookup, setLookup] = useState<AdminPushSubscriptionLookup | null>(null);
  const [deliveries, setDeliveries] = useState<PushDeliveryEvent[]>([]);
  const [summary, setSummary] = useState<Record<string, number>>({});
  const [deliveryFilter, setDeliveryFilter] = useState("");

  const apply = useCallback((data: PushProviderSettings) => {
    setSettings(data);
    setPushEnabled(data.push_enabled);
    setProvider((data.provider as PushProviderMode) || "log");
    setSubject(data.vapid_subject || "mailto:support@padeya.com");
    setPublicKey(data.vapid_public_key || "");
    setPrivateKey("");
  }, []);

  const loadDeliveries = useCallback(async (status?: string) => {
    const data = await fetchAdminPushDeliveries({
      status: status || undefined,
      limit: 40,
    });
    setDeliveries(data.items);
    setSummary(data.summary || {});
  }, []);

  const load = useCallback(async () => {
    const data = await fetchAdminPushSettings();
    apply(data);
    await loadDeliveries(deliveryFilter);
  }, [apply, loadDeliveries, deliveryFilter]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load push settings",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNote(null);
    try {
      const data = await updateAdminPushSettings({
        push_enabled: pushEnabled,
        provider,
        vapid_subject: subject.trim(),
        vapid_public_key: publicKey.trim() || null,
        vapid_private_key: privateKey.trim() || null,
      });
      apply(data);
      setNote("Push settings saved.");
      await loadDeliveries(deliveryFilter);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  async function onGenerate() {
    setSaving(true);
    setError(null);
    try {
      const data = await updateAdminPushSettings({
        generate_vapid_keys: true,
        push_enabled: pushEnabled,
        provider,
        vapid_subject: subject.trim(),
      });
      apply(data);
      setNote("New VAPID keys generated. Private key is stored encrypted and never shown.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not generate keys");
    } finally {
      setSaving(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Push notification settings"
      description="Manage Pàdéyá browser push. VAPID private keys are encrypted at rest and never returned to the browser."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/email/settings">
            <Button size="sm" variant="secondary">
              Email settings
            </Button>
          </Link>
          <Link href="/admin">
            <Button size="sm" variant="ghost">
              Admin hub
            </Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Status">
          {note}
        </Alert>
      ) : null}

      {settings ? (
        <div className="mb-4 flex flex-wrap gap-2 text-sm text-muted-foreground">
          <Badge tone={settings.push_enabled ? "success" : "neutral"} size="sm">
            {settings.push_enabled ? "Push on" : "Push off"}
          </Badge>
          <Badge tone="neutral" size="sm">
            Provider: {settings.provider}
          </Badge>
          {settings.vapid_private_configured ? (
            <span>Private key: {settings.vapid_private_hint}</span>
          ) : (
            <span>Private key: not configured</span>
          )}
          {settings.last_test_at ? (
            <span>
              Last test: {formatDateTime(settings.last_test_at)} ·{" "}
              {settings.last_test_status}
              {settings.last_test_error ? ` (${settings.last_test_error})` : ""}
            </span>
          ) : null}
        </div>
      ) : null}

      <Card className="mb-4 p-5">
        <form className="space-y-4" onSubmit={onSave}>
          <Switch
            id="push-enabled"
            checked={pushEnabled}
            onCheckedChange={setPushEnabled}
            label="Push delivery enabled"
            description="Global kill switch. When off, no pushes are sent (subscriptions are kept)."
          />
          <Select
            label="Push provider mode"
            value={provider}
            onChange={(e) => setProvider(e.target.value as PushProviderMode)}
            hint="log records attempts only. web_push delivers to opted-in browsers."
          >
            <option value="log">log (safe / no browser send)</option>
            <option value="web_push">web_push (browser delivery)</option>
          </Select>
          <Input
            label="VAPID subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            hint="mailto:support@padeya.com or https://padeya.com"
          />
          <Input
            label="VAPID public key"
            value={publicKey}
            onChange={(e) => setPublicKey(e.target.value)}
            hint="Shared with browsers for subscribe — or generate a new keypair"
          />
          <Input
            label="VAPID private key"
            type="password"
            value={privateKey}
            onChange={(e) => setPrivateKey(e.target.value)}
            autoComplete="new-password"
            hint={
              settings?.vapid_private_configured
                ? "Leave blank to keep the existing encrypted key — it is never shown again"
                : "Paste PEM or generate keys (encrypted before save)"
            }
          />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={saving || testing}>
              {saving ? "Saving…" : "Save settings"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={saving || testing}
              onClick={() => void onGenerate()}
            >
              Generate VAPID keys
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={saving || testing}
              onClick={() =>
                void disableAdminPush()
                  .then(apply)
                  .then(() => setNote("Push disabled globally."))
                  .catch((err) =>
                    setError(
                      err instanceof ApiError ? err.detail : "Could not disable",
                    ),
                  )
              }
            >
              Disable push globally
            </Button>
          </div>
        </form>
      </Card>

      <Card className="mb-4 space-y-4 p-5">
        <div>
          <h2 className="font-bold">Test push</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Fixed copy: “Pàdéyá test notification” · “Push notifications are working.” ·
            opens /dashboard/notifications. Recipient must have an active device.
          </p>
        </div>

        <div className="rounded-lg border border-border bg-muted/30 p-4">
          <p className="text-sm font-semibold text-foreground">This admin browser</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Enable push below first, then send a test to yourself.
          </p>
          <div className="mt-3">
            <PushSettingsPanel />
          </div>
          <Button
            type="button"
            className="mt-3"
            variant="secondary"
            disabled={saving || testing}
            onClick={() => {
              setTesting(true);
              setError(null);
              setNote(null);
              void testAdminPush()
                .then(async (r) => {
                  setNote(r.message || "Test sent to your devices");
                  await loadDeliveries(deliveryFilter);
                  const refreshed = await fetchAdminPushSettings();
                  apply(refreshed);
                })
                .catch((err) =>
                  setError(err instanceof ApiError ? err.detail : "Test failed"),
                )
                .finally(() => setTesting(false));
            }}
          >
            {testing ? "Testing…" : "Send test push to me"}
          </Button>
        </div>

        <div className="space-y-3 border-t border-border pt-4">
          <p className="text-sm font-semibold text-foreground">Selected user</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="User email"
              value={testTargetEmail}
              onChange={(e) => setTestTargetEmail(e.target.value)}
              placeholder="fan@example.com"
              autoComplete="off"
            />
            <Input
              label="User id (optional)"
              value={testTargetUserId}
              onChange={(e) => setTestTargetUserId(e.target.value)}
              placeholder="uuid"
              autoComplete="off"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="ghost"
              disabled={lookingUp || testing || (!testTargetEmail.trim() && !testTargetUserId.trim())}
              onClick={() => {
                setLookingUp(true);
                setError(null);
                void lookupAdminPushSubscriptions({
                  email: testTargetEmail,
                  user_id: testTargetUserId,
                })
                  .then((data) => {
                    setLookup(data);
                    setNote(
                      data.has_active_device
                        ? `${data.email || data.user_id} has ${data.active_subscription_count} active device(s).`
                        : `${data.email || data.user_id} has no active push devices.`,
                    );
                  })
                  .catch((err) =>
                    setError(
                      err instanceof ApiError
                        ? err.detail
                        : "Could not look up subscriptions",
                    ),
                  )
                  .finally(() => setLookingUp(false));
              }}
            >
              {lookingUp ? "Checking…" : "Check active devices"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={
                testing || lookingUp || (!testTargetEmail.trim() && !testTargetUserId.trim())
              }
              onClick={() => {
                setTesting(true);
                setError(null);
                setNote(null);
                void testAdminPushToUser({
                  email: testTargetEmail,
                  user_id: testTargetUserId,
                })
                  .then(async (r) => {
                    setNote(r.message || "Test sent");
                    await loadDeliveries(deliveryFilter);
                    const refreshed = await fetchAdminPushSettings();
                    apply(refreshed);
                    try {
                      const status = await lookupAdminPushSubscriptions({
                        email: testTargetEmail,
                        user_id: testTargetUserId,
                      });
                      setLookup(status);
                    } catch {
                      /* ignore refresh failure */
                    }
                  })
                  .catch((err) =>
                    setError(err instanceof ApiError ? err.detail : "Test failed"),
                  )
                  .finally(() => setTesting(false));
              }}
            >
              {testing ? "Testing…" : "Send test push to user"}
            </Button>
          </div>
          {lookup ? (
            <div className="rounded-lg border border-border p-3 text-sm">
              <div className="flex flex-wrap gap-2">
                <Badge
                  tone={lookup.has_active_device ? "success" : "danger"}
                  size="sm"
                >
                  {lookup.has_active_device
                    ? `${lookup.active_subscription_count} active device(s)`
                    : "No active devices"}
                </Badge>
                <span className="text-muted-foreground">
                  {lookup.full_name || "User"} · {lookup.email || lookup.user_id}
                </span>
              </div>
              {lookup.devices.length > 0 ? (
                <ul className="mt-2 space-y-1 text-muted-foreground">
                  {lookup.devices.map((d) => (
                    <li key={d.id}>
                      {d.device_label || d.platform || "Device"}
                      {d.endpoint_hint ? ` · ${d.endpoint_hint}` : ""}
                      {d.failure_count > 0 ? ` · failures ${d.failure_count}` : ""}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-muted-foreground">
                  No active push devices for this user. They must enable browser
                  notifications on Pàdéyá before a test can be sent.
                </p>
              )}
            </div>
          ) : null}
        </div>
      </Card>

      <Card className="mb-4 space-y-3 p-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-bold">Delivery status</h2>
            <p className="text-sm text-muted-foreground">
              Recent push attempts. Failed rows never include VAPID secrets.
            </p>
          </div>
          <Select
            label="Filter"
            value={deliveryFilter}
            onChange={(e) => {
              const next = e.target.value;
              setDeliveryFilter(next);
              void loadDeliveries(next).catch((err) =>
                setError(
                  err instanceof ApiError ? err.detail : "Could not load deliveries",
                ),
              );
            }}
          >
            <option value="">All</option>
            <option value="sent">sent</option>
            <option value="failed">failed</option>
            <option value="logged">logged</option>
            <option value="pending">pending</option>
            <option value="revoked">revoked</option>
          </Select>
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          {["sent", "failed", "logged", "pending", "revoked", "total"].map((key) => (
            <Badge key={key} tone={key === "failed" ? "danger" : "neutral"} size="sm">
              {key}: {summary[key] ?? 0}
            </Badge>
          ))}
        </div>
        {deliveries.length === 0 ? (
          <p className="text-sm text-muted-foreground">No delivery events yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="py-2 pr-3 font-semibold">When</th>
                  <th className="py-2 pr-3 font-semibold">Status</th>
                  <th className="py-2 pr-3 font-semibold">Kind</th>
                  <th className="py-2 font-semibold">Error</th>
                </tr>
              </thead>
              <tbody>
                {deliveries.map((row) => (
                  <tr key={row.id} className="border-t border-border/60">
                    <td className="py-2 pr-3 whitespace-nowrap">
                      {formatDateTime(row.created_at)}
                    </td>
                    <td className="py-2 pr-3">
                      <Badge
                        tone={
                          row.status === "failed"
                            ? "danger"
                            : row.status === "sent" || row.status === "logged"
                              ? "success"
                              : "neutral"
                        }
                        size="sm"
                      >
                        {row.status}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3 font-mono text-xs">{row.kind}</td>
                    <td className="py-2 text-xs text-muted-foreground">
                      {row.error_message || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </DashboardShell>
  );
}

/** Push VAPID / provider controls — super_admin only (API also requires admin.full_access). */
export default function AdminPushSettingsPage() {
  return (
    <RequireAuth roles={["super_admin"]}>
      <AdminPushSettingsPageInner />
    </RequireAuth>
  );
}
