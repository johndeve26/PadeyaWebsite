"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { AdminAmbassadorsNav } from "@/components/ambassadors/AdminAmbassadorsNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmAction,
  EmptyState,
  Input,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import {
  adminEnrollmentScopeLabel,
  overviewArrangementHint,
  overviewCommissionHint,
} from "@/lib/ambassador-frontend-alignment";
import { track } from "@/lib/analytics";
import { ApiError, isTimeoutError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import {
  blockAdminAmbassador,
  fetchAdminAmbassadorSettings,
  fetchAdminAmbassadors,
  fetchAdminReferralSummary,
  unblockAdminAmbassador,
  updateAdminAmbassadorSettings,
  type AdminReferralOverviewSummary,
} from "@/lib/promos-api";
import type {
  AdminAmbassadorRow,
  AmbassadorPlatformSettings,
} from "@/lib/types/promos";

function money(v: unknown): string {
  return formatNgn(Number(v ?? 0) || 0);
}

function errMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) return err.detail;
  if (isTimeoutError(err)) return "Request timed out — retry in a moment.";
  return fallback;
}

const WORKSPACE_LINKS = [
  {
    href: "/admin/ambassadors/programs",
    title: "Programs",
    description: "Manage Pàdéyá-wide programs and enrollments",
  },
  {
    href: "/admin/ambassadors/campaigns",
    title: "Campaigns",
    description: "Manage existing event-scoped campaigns",
  },
  {
    href: "/admin/ambassadors/liabilities",
    title: "Liabilities",
    description: "Review host-funded and Pàdéyá-funded commission",
  },
  {
    href: "/admin/ambassadors/conversions",
    title: "Conversions",
    description: "Review attributed purchases",
  },
  {
    href: "/admin/ambassadors/payouts",
    title: "Payouts",
    description: "Manage approved ambassador payments",
  },
  {
    href: "/admin/ambassadors/reports",
    title: "Reports",
    description: "Review referral performance",
  },
] as const;

export default function AdminAmbassadorsPage() {
  const { authInitialized, user } = useAuth();
  const [settings, setSettings] = useState<AmbassadorPlatformSettings | null>(
    null,
  );
  const [summary, setSummary] = useState<AdminReferralOverviewSummary | null>(
    null,
  );
  const [rows, setRows] = useState<AdminAmbassadorRow[]>([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadList(search = q) {
    setRows(await fetchAdminAmbassadors({ q: search || undefined }));
  }

  async function loadOverview() {
    setError(null);
    const [sResult, sumResult, listResult] = await Promise.allSettled([
      fetchAdminAmbassadorSettings(),
      fetchAdminReferralSummary(),
      fetchAdminAmbassadors({}),
    ]);

    if (sResult.status === "fulfilled") {
      setSettings(sResult.value);
    } else {
      setError(errMessage(sResult.reason, "Failed to load Ambassadors"));
    }

    if (sumResult.status === "fulfilled") {
      setSummary(sumResult.value);
      setSummaryError(null);
    } else {
      setSummary(null);
      setSummaryError(
        errMessage(sumResult.reason, "Could not load referral summary"),
      );
    }

    if (listResult.status === "fulfilled") {
      setRows(listResult.value);
    } else if (sResult.status === "fulfilled") {
      setError(errMessage(listResult.reason, "Could not load ambassadors"));
    }
  }

  useEffect(() => {
    if (!authInitialized || !user) return;
    let active = true;
    void (async () => {
      await loadOverview();
      if (!active) return;
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authInitialized, user?.id]);

  async function setEnabled(next: boolean) {
    setBusy(true);
    setError(null);
    try {
      const updated = await updateAdminAmbassadorSettings({ enabled: next });
      setSettings(updated);
      track("admin_ambassador_feature_toggle", {
        metadata: { enabled: next },
        dedupeTtlMs: 1_000,
      });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not update settings",
      );
      throw err;
    } finally {
      setBusy(false);
    }
  }

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      track("admin_ambassador_search", {
        metadata: { has_query: Boolean(q.trim()) },
        dedupeTtlMs: 2_000,
      });
      await loadList();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Search failed");
    }
  }

  async function applyBlock(row: AdminAmbassadorRow, block: boolean) {
    setBusy(true);
    setError(null);
    try {
      if (block) {
        await blockAdminAmbassador(row.id);
      } else {
        await unblockAdminAmbassador(row.id);
      }
      track("admin_ambassador_block_toggle", {
        metadata: { blocked: block },
        dedupeTtlMs: 1_000,
      });
      await loadList();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Block action failed");
      throw err;
    } finally {
      setBusy(false);
    }
  }

  const arrangements = Number(summary?.active_arrangements ?? 0);
  const platformPrograms = Number(summary?.active_platform_programs ?? 0);
  const hostCampaigns = Number(summary?.active_host_campaigns ?? 0);
  const uniqueAmbs = Number(summary?.unique_active_ambassadors ?? 0);
  const platEnroll = Number(summary?.platform_enrollments_active ?? 0);
  const hostEnroll = Number(summary?.host_enrollments_active ?? 0);
  const converted = Number(summary?.converted_orders ?? 0);
  const attributed = Number(summary?.attributed_items ?? 0);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Ambassadors"
      description="Operational hub for Pàdéyá Ambassadors — platform programs, host campaigns, and ledger-backed referral totals."
      actions={
        <Link href="/admin/audit-logs">
          <Button variant="secondary">Audit logs</Button>
        </Link>
      }
    >
      <AdminAmbassadorsNav />
      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}
      {summaryError ? (
        <Alert tone="warning" title="Summary unavailable">
          {summaryError}. List and settings may still work.{" "}
          <button
            type="button"
            className="underline"
            onClick={() => {
              setSummaryError(null);
              void loadOverview().catch(() => undefined);
            }}
          >
            Retry
          </button>
        </Alert>
      ) : null}

      {!settings ? (
        <SkeletonLoader lines={4} />
      ) : (
        <div className="space-y-6">
          <Card className="flex flex-wrap items-center justify-between gap-4 p-5">
            <div className="max-w-xl">
              <p className="text-sm font-semibold text-foreground">
                Global referral switch
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                When disabled, Pàdéyá stops open Ambassador join and eligible
                event listings. Existing earnings, reversals, liabilities, and
                payout history remain available. Disabling does not delete
                programs, referral codes, or recalculate host settlement.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Badge tone={settings.enabled ? "success" : "warning"}>
                {settings.enabled ? "Enabled" : "Disabled"}
              </Badge>
              {settings.enabled ? (
                <ConfirmAction
                  label="Disable globally"
                  title="Disable Ambassadors?"
                  description="Open join and eligible listings will stop. Existing enrollments, earnings, reversals, and liabilities stay available. Attribution for existing enrollments is not wiped."
                  confirmLabel="Disable"
                  tone="danger"
                  busy={busy}
                  disabled={busy}
                  onConfirm={() => setEnabled(false)}
                />
              ) : (
                <Button
                  onClick={() => void setEnabled(true)}
                  disabled={busy}
                >
                  Enable globally
                </Button>
              )}
            </div>
          </Card>

          {!summary && !summaryError ? (
            <SkeletonLoader lines={3} />
          ) : summary ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div
                aria-label={`Active programs and campaigns: ${arrangements}. ${platformPrograms} Pàdéyá programs and ${hostCampaigns} host campaigns.`}
              >
                <StatCard
                  title="Active programs & campaigns"
                  value={String(arrangements)}
                  hint={overviewArrangementHint(platformPrograms, hostCampaigns)}
                />
              </div>
              <div
                aria-label={`Active unique ambassadors: ${uniqueAmbs}. ${platEnroll} platform enrollments and ${hostEnroll} host campaign enrollments.`}
              >
                <StatCard
                  title="Active ambassadors"
                  value={String(uniqueAmbs)}
                  hint={`${platEnroll} platform enrollments · ${hostEnroll} host campaign enrollments`}
                />
              </div>
              <div
                aria-label={`Converted orders: ${converted}.${attributed ? ` ${attributed} attributed items.` : ""}`}
              >
                <StatCard
                  title="Converted orders"
                  value={String(converted)}
                  hint={
                    attributed
                      ? `${attributed} attributed items`
                      : "Distinct referred orders"
                  }
                />
              </div>
              <div
                aria-label={`Commission owed: ${money(summary.commission_owed_total)} total. ${money(summary.host_funded_owed)} host-funded and ${money(summary.platform_funded_owed)} funded by Pàdéyá.`}
              >
                <StatCard
                  title="Commission owed"
                  value={money(summary.commission_owed_total)}
                  hint={overviewCommissionHint(
                    money(summary.host_funded_owed),
                    money(summary.platform_funded_owed),
                  )}
                />
              </div>
            </div>
          ) : null}

          <section className="space-y-3" aria-label="Ambassador workspaces">
            <h2 className="text-lg font-semibold text-foreground">
              Workspaces
            </h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {WORKSPACE_LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="block"
                  onClick={() =>
                    track("admin_ambassador_overview_link", {
                      metadata: { destination: link.href },
                      dedupeTtlMs: 1_000,
                    })
                  }
                >
                  <Card className="h-full p-4 transition-colors hover:border-[var(--brand-green)]">
                    <p className="font-semibold text-foreground">{link.title}</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {link.description}
                    </p>
                  </Card>
                </Link>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-foreground">
              Ambassadors
            </h2>
            <form onSubmit={onSearch} className="flex flex-wrap gap-2">
              <Input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search name, email, or code"
                className="max-w-sm"
                aria-label="Search ambassadors"
              />
              <Button type="submit" variant="secondary">
                Search
              </Button>
            </form>
            {rows.length === 0 ? (
              <EmptyState
                title="No ambassadors yet"
                description="Platform enrollments and open host campaigns will populate this list."
              />
            ) : (
              <div className="space-y-2">
                {rows.map((row) => {
                  const isPlatform = row.program_kind === "platform_wide";
                  return (
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
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                          <Badge tone={isPlatform ? "success" : "neutral"}>
                            {adminEnrollmentScopeLabel(row.program_kind)}
                          </Badge>
                          <span>
                            {isPlatform
                              ? "Platform enrollment"
                              : row.event_title || "Event campaign"}{" "}
                            · {row.status}
                            {row.ambassadors_blocked ? " · blocked" : ""}
                          </span>
                        </div>
                      </div>
                      {row.ambassadors_blocked ? (
                        <ConfirmAction
                          label="Unblock"
                          title="Unblock this ambassador?"
                          description="Unblocking restores eligibility to join campaigns and receive rewards for this linked user account, subject to other restrictions."
                          confirmLabel="Unblock"
                          busy={busy}
                          disabled={busy || !row.user_id}
                          onConfirm={() => applyBlock(row, false)}
                        />
                      ) : (
                        <ConfirmAction
                          label="Block"
                          title="Block this ambassador?"
                          description="Blocking prevents this linked user from joining new Ambassador campaigns and from earning new referral attribution across enrollments. Historical earnings, payouts, and ledger entries are not deleted."
                          confirmLabel="Block"
                          tone="danger"
                          busy={busy}
                          disabled={busy || !row.user_id}
                          onConfirm={() => applyBlock(row, true)}
                        />
                      )}
                    </Card>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      )}
    </DashboardShell>
  );
}
