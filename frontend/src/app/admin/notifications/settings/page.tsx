"use client";

import { useCallback, useEffect, useState } from "react";

import { AdminNotificationsNav } from "@/components/admin/AdminNotificationsNav";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Card,
  Select,
  SkeletonLoader,
  Switch,
  useToast,
} from "@/components/ui";
import {
  fetchAdminNotificationSettings,
  updateAdminNotificationSetting,
  type AdminNotificationSetting,
} from "@/lib/admin-notifications/api";
import { ApiError } from "@/lib/api";

const AUDIENCE_OPTIONS = [
  { value: "context_recipients", label: "Context recipients" },
  { value: "host_followers", label: "Host followers" },
  { value: "event_ticket_buyers", label: "Event ticket buyers" },
  { value: "checked_in_attendees", label: "Checked-in attendees" },
  { value: "vip_ticket_holders", label: "VIP / VVIP" },
  { value: "past_buyers", label: "Past buyers" },
  { value: "past_merch_buyers", label: "Past merch buyers" },
  { value: "vault_members", label: "Vault members" },
  { value: "ambassadors", label: "Ambassadors" },
  { value: "host_team_members", label: "Host team" },
  { value: "all_users", label: "All users" },
  { value: "selected_users", label: "Selected users" },
  { value: "role", label: "Role filter" },
  { value: "geo", label: "Geo filter" },
];

export default function AdminNotificationSettingsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<AdminNotificationSetting[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setRows(await fetchAdminNotificationSettings());
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load settings");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) void load();
    });
    return () => {
      cancelled = true;
    };
  }, [load]);

  async function patch(
    typeKey: string,
    body: Parameters<typeof updateAdminNotificationSetting>[1],
  ) {
    setBusyKey(typeKey);
    setError(null);
    try {
      const next = await updateAdminNotificationSetting(typeKey, body);
      setRows((prev) =>
        (prev || []).map((r) => (r.type_key === typeKey ? next : r)),
      );
      toast.push({ tone: "success", title: "Setting saved" });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <RequireAuth roles={["super_admin"]}>
      <DashboardShell
        tone="soft"
        eyebrow="Admin · Notifications"
        title="Notification settings"
        description="Toggle each platform event, channels, and default audience. Critical types need super_admin to disable."
      >
        <AdminNotificationsNav />
        {error ? (
          <Alert tone="danger" title="Error">
            {error}
          </Alert>
        ) : null}

        {!rows ? (
          <SkeletonLoader lines={6} />
        ) : (
          <div className="space-y-3">
            {rows.map((row) => (
              <Card key={row.type_key} className="space-y-3 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-bold text-foreground">{row.label}</h3>
                      <Badge tone="neutral" size="sm">
                        {row.classification}
                      </Badge>
                      {row.critical ? (
                        <Badge tone="danger" size="sm">
                          Critical
                        </Badge>
                      ) : null}
                    </div>
                    <p className="text-sm text-muted-foreground">{row.description}</p>
                    <p className="font-mono text-xs text-muted-foreground">
                      {row.type_key}
                    </p>
                  </div>
                  <Switch
                    checked={row.enabled}
                    disabled={busyKey === row.type_key}
                    onCheckedChange={(enabled) =>
                      void patch(row.type_key, { enabled })
                    }
                    label={row.enabled ? "On" : "Off"}
                  />
                </div>

                <div className="flex flex-wrap gap-4 text-sm">
                  {(
                    [
                      ["in_app", "In-app"],
                      ["push", "Push"],
                      ["email", "Email"],
                    ] as const
                  ).map(([key, label]) => (
                    <label key={key} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={row.channels[key]}
                        disabled={
                          busyKey === row.type_key ||
                          (key === "push" && Boolean(row.push_unavailable_reason))
                        }
                        onChange={(e) =>
                          void patch(row.type_key, {
                            channels: { [key]: e.target.checked },
                          })
                        }
                      />
                      {label}
                    </label>
                  ))}
                </div>
                {row.push_unavailable_reason ? (
                  <p className="text-xs text-muted-foreground">
                    Push unavailable: {row.push_unavailable_reason}
                  </p>
                ) : null}

                <div className="max-w-sm">
                  <Select
                    label="Audience"
                    value={row.audience}
                    onChange={(e) =>
                      void patch(row.type_key, { audience: e.target.value })
                    }
                    disabled={busyKey === row.type_key}
                  >
                    {AUDIENCE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </Select>
                </div>
              </Card>
            ))}
          </div>
        )}
      </DashboardShell>
    </RequireAuth>
  );
}
