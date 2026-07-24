"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { AdminAmbassadorsNav } from "@/components/ambassadors/AdminAmbassadorsNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  blockAdminAmbassador,
  fetchAdminAmbassadorReports,
  fetchAdminAmbassadorSettings,
  fetchAdminAmbassadors,
  unblockAdminAmbassador,
  updateAdminAmbassadorSettings,
} from "@/lib/promos-api";
import type {
  AdminAmbassadorRow,
  AmbassadorPlatformSettings,
  AmbassadorReportsSummary,
} from "@/lib/types/promos";

export default function AdminAmbassadorsPage() {
  const [settings, setSettings] = useState<AmbassadorPlatformSettings | null>(null);
  const [summary, setSummary] = useState<AmbassadorReportsSummary | null>(null);
  const [rows, setRows] = useState<AdminAmbassadorRow[]>([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load(search = q) {
    const [s, report, ambs] = await Promise.all([
      fetchAdminAmbassadorSettings(),
      fetchAdminAmbassadorReports(),
      fetchAdminAmbassadors({ q: search || undefined }),
    ]);
    setSettings(s);
    setSummary(report);
    setRows(ambs);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load("");
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load Ambassadors");
        }
      }
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function toggleFeature() {
    if (!settings) return;
    setBusy(true);
    setError(null);
    try {
      setSettings(
        await updateAdminAmbassadorSettings({ enabled: !settings.enabled }),
      );
      setSummary(await fetchAdminAmbassadorReports());
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not update settings");
    } finally {
      setBusy(false);
    }
  }

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      setRows(await fetchAdminAmbassadors({ q: q || undefined }));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Search failed");
    }
  }

  async function toggleBlock(row: AdminAmbassadorRow) {
    setBusy(true);
    setError(null);
    try {
      if (row.ambassadors_blocked) {
        await unblockAdminAmbassador(row.id);
      } else {
        await blockAdminAmbassador(row.id);
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Block action failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Ambassadors"
      description="Manage all Pàdéyá Ambassadors activity across campaigns, conversions, and rewards."
      actions={
        <Link href="/admin/audit-logs">
          <Button variant="secondary">Audit logs</Button>
        </Link>
      }
    >
      <AdminAmbassadorsNav />
      {error ? <Alert tone="danger" title="Something went wrong">{error}</Alert> : null}

      {!settings || !summary ? (
        <SkeletonLoader lines={4} />
      ) : (
        <div className="space-y-6">
          <Card className="flex flex-wrap items-center justify-between gap-4 p-5">
            <div>
              <p className="text-sm font-semibold text-foreground">
                Platform feature
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                When disabled, open join and eligible listings stop. Existing
                enrollments stay, but new attribution is gated at join.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Badge tone={settings.enabled ? "success" : "warning"}>
                {settings.enabled ? "Enabled" : "Disabled"}
              </Badge>
              <Button onClick={() => void toggleFeature()} disabled={busy}>
                {settings.enabled ? "Disable globally" : "Enable globally"}
              </Button>
            </div>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard title="Live campaigns" value={String(summary.campaigns_live)} />
            <StatCard title="Active ambassadors"
              value={String(summary.ambassadors_active)}
            />
            <StatCard title="Conversions" value={String(summary.conversions_active)} />
            <StatCard title="Commission owed"
              value={`₦${Number(summary.commission_owed).toLocaleString()}`}
            />
          </div>

          <div className="flex flex-wrap gap-3">
            <Link href="/admin/ambassadors/campaigns">
              <Button>Campaigns</Button>
            </Link>
            <Link href="/admin/ambassadors/conversions">
              <Button variant="secondary">Conversions</Button>
            </Link>
            <Link href="/admin/ambassadors/payouts">
              <Button variant="secondary">Payouts</Button>
            </Link>
            <Link href="/admin/ambassadors/reports">
              <Button variant="secondary">Reports</Button>
            </Link>
          </div>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-foreground">Ambassadors</h2>
            <form onSubmit={onSearch} className="flex flex-wrap gap-2">
              <Input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search name, email, or code"
                className="max-w-sm"
              />
              <Button type="submit" variant="secondary">
                Search
              </Button>
            </form>
            {rows.length === 0 ? (
              <EmptyState
                title="No ambassadors yet"
                description="Open campaigns will populate this list as users join."
              />
            ) : (
              <div className="space-y-2">
                {rows.map((row) => (
                  <Card
                    key={row.id}
                    className="flex flex-wrap items-center justify-between gap-3 p-4"
                  >
                    <div>
                      <p className="font-semibold text-foreground">
                        {row.display_name}{" "}
                        <span className="font-mono text-sm text-muted-foreground">
                          {row.referral_code}
                        </span>
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {row.event_title || "Host partner"} · {row.status}
                        {row.ambassadors_blocked ? " · blocked" : ""}
                      </p>
                    </div>
                    <Button
                      variant="secondary"
                      disabled={busy || !row.user_id}
                      onClick={() => void toggleBlock(row)}
                    >
                      {row.ambassadors_blocked ? "Unblock" : "Block"}
                    </Button>
                  </Card>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </DashboardShell>
  );
}
