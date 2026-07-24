"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Input,
  Select,
  Switch,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  maintenanceDatetimeLocalToIso,
  maintenanceIsoToDatetimeLocal,
} from "@/lib/maintenance-datetime";
import {
  createMaintenanceBypass,
  createMaintenanceSchedule,
  fetchMaintenanceAdmin,
  patchMaintenanceSection,
  patchMaintenanceSettings,
  type MaintenanceDashboard,
  type MaintenanceMode,
} from "@/lib/maintenance-api";

const MODE_OPTIONS: { value: MaintenanceMode; label: string }[] = [
  { value: "off", label: "Off" },
  { value: "scheduled", label: "Scheduled" },
  { value: "active", label: "Full-site active" },
  { value: "read_only", label: "Read-only" },
  { value: "section_only", label: "Section-only" },
];

export default function AdminMaintenancePage() {
  const toast = useToast();
  const [data, setData] = useState<MaintenanceDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [bypassToken, setBypassToken] = useState<string | null>(null);

  const [schedTitle, setSchedTitle] = useState("Scheduled maintenance");
  const [schedStart, setSchedStart] = useState("");
  const [schedEnd, setSchedEnd] = useState("");

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await fetchMaintenanceAdmin();
      setData(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load");
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load() hydrates dashboard from API
    void load();
  }, [load]);

  async function saveMode(mode: MaintenanceMode) {
    setBusy(true);
    try {
      const settings = await patchMaintenanceSettings({ mode });
      setData((d) => (d ? { ...d, settings } : d));
      toast.push({ tone: "success", title: "Maintenance updated" });
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Update failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function saveMessages() {
    if (!data) return;
    setBusy(true);
    try {
      const settings = await patchMaintenanceSettings({
        title: data.settings.title,
        message: data.settings.message,
        expected_back_at: data.settings.expected_back_at,
        show_countdown: data.settings.show_countdown,
      });
      setData((d) => (d ? { ...d, settings } : d));
      toast.push({ tone: "success", title: "Saved" });
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Save failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function toggleSection(key: string, enabled: boolean) {
    setBusy(true);
    try {
      const section = await patchMaintenanceSection(key, { enabled });
      setData((d) =>
        d
          ? {
              ...d,
              sections: d.sections.map((s) =>
                s.section_key === key ? section : s,
              ),
            }
          : d,
      );
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Section update failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function createSchedule() {
    if (!schedStart) return;
    setBusy(true);
    try {
      await createMaintenanceSchedule({
        title: schedTitle,
        message: data?.settings.message || "",
        target_mode: "active",
        starts_at: new Date(schedStart).toISOString(),
        ends_at: schedEnd ? new Date(schedEnd).toISOString() : null,
        show_countdown: true,
        auto_enable: true,
        auto_disable: true,
      });
      toast.push({ tone: "success", title: "Schedule created" });
      await load();
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Schedule failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function issueBypass() {
    setBusy(true);
    try {
      const res = await createMaintenanceBypass(8);
      setBypassToken(res.token);
      toast.push({
        tone: "success",
        title: "Bypass token created",
        description: "Shown once — store securely.",
      });
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Bypass failed",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Platform"
      title="Maintenance"
      description="Full-site, read-only, and section maintenance for Pàdéyá."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link
            href="/admin/platform/maintenance/history"
            className="inline-flex h-9 items-center rounded-[var(--radius-sm)] border border-border bg-surface-elevated px-3.5 text-sm font-semibold text-foreground shadow-[var(--shadow-soft)] hover:bg-surface-muted"
          >
            History
          </Link>
          <Link
            href="/admin/platform/maintenance/notifications"
            className="inline-flex h-9 items-center rounded-[var(--radius-sm)] border border-border bg-surface-elevated px-3.5 text-sm font-semibold text-foreground shadow-[var(--shadow-soft)] hover:bg-surface-muted"
          >
            Notifications
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}

      {!data ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : (
        <div className="space-y-10">
          <section className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-lg font-bold text-heading">Global mode</h2>
              <Badge tone={data.settings.mode === "off" ? "neutral" : "warning"}>
                {data.settings.mode}
              </Badge>
            </div>
            <Select
              label="Mode"
              value={data.settings.mode}
              onChange={(e) => void saveMode(e.target.value as MaintenanceMode)}
              disabled={busy}
            >
              {MODE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
            <Input
              label="Title"
              value={data.settings.title}
              onChange={(e) =>
                setData({
                  ...data,
                  settings: { ...data.settings, title: e.target.value },
                })
              }
            />
            <Textarea
              label="User-facing message"
              value={data.settings.message}
              onChange={(e) =>
                setData({
                  ...data,
                  settings: { ...data.settings, message: e.target.value },
                })
              }
              rows={3}
            />
            <Input
              label="Expected back at"
              hint="Pick date and time in your timezone. Stored as UTC for the public maintenance page."
              type="datetime-local"
              value={maintenanceIsoToDatetimeLocal(data.settings.expected_back_at)}
              onChange={(e) =>
                setData({
                  ...data,
                  settings: {
                    ...data.settings,
                    expected_back_at: maintenanceDatetimeLocalToIso(e.target.value),
                  },
                })
              }
            />
            <Switch
              checked={data.settings.show_countdown}
              onCheckedChange={(v) =>
                setData({
                  ...data,
                  settings: { ...data.settings, show_countdown: v },
                })
              }
              label="Show countdown"
            />
            <Button size="sm" disabled={busy} onClick={() => void saveMessages()}>
              Save message
            </Button>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-heading">Sections</h2>
            <p className="text-sm text-muted-foreground">
              Disable specific areas. Use with mode “section_only” or leave
              sections enabled while global is off.
            </p>
            <ul className="divide-y divide-border rounded-[var(--radius-md)] border border-border">
              {data.sections.map((s) => (
                <li
                  key={s.section_key}
                  className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
                >
                  <div>
                    <p className="text-sm font-semibold text-heading">{s.label}</p>
                    <p className="text-xs text-muted-foreground">{s.section_key}</p>
                  </div>
                  <Switch
                    checked={s.enabled}
                    disabled={busy}
                    onCheckedChange={(v) => void toggleSection(s.section_key, v)}
                    label={s.enabled ? "On" : "Off"}
                  />
                </li>
              ))}
            </ul>
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-bold text-heading">Schedule</h2>
            <Input
              label="Title"
              value={schedTitle}
              onChange={(e) => setSchedTitle(e.target.value)}
            />
            <Input
              label="Starts at"
              type="datetime-local"
              value={schedStart}
              onChange={(e) => setSchedStart(e.target.value)}
            />
            <Input
              label="Ends at"
              type="datetime-local"
              value={schedEnd}
              onChange={(e) => setSchedEnd(e.target.value)}
            />
            <Button size="sm" disabled={busy} onClick={() => void createSchedule()}>
              Create schedule
            </Button>
            {data.schedules.length ? (
              <ul className="space-y-2 text-sm">
                {data.schedules.map((s) => (
                  <li key={s.id} className="text-muted-foreground">
                    <Badge size="sm">{s.status}</Badge> {s.title} — {s.starts_at}
                  </li>
                ))}
              </ul>
            ) : null}
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-bold text-heading">Admin bypass</h2>
            <p className="text-sm text-muted-foreground">
              Issue a short-lived token. Send header{" "}
              <code className="font-mono text-xs">X-Maintenance-Bypass</code> on
              product API calls. Never expose publicly.
            </p>
            <Button
              size="sm"
              variant="secondary"
              disabled={busy}
              onClick={() => void issueBypass()}
            >
              Generate bypass token
            </Button>
            {bypassToken ? (
              <Alert tone="warning" title="Bypass token (once)">
                <code className="break-all text-xs">{bypassToken}</code>
              </Alert>
            ) : null}
          </section>
        </div>
      )}
    </DashboardShell>
  );
}
