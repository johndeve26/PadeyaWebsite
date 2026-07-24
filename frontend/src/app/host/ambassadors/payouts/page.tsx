"use client";

import { useEffect, useMemo, useState } from "react";

import { HostAmbassadorsNav } from "@/components/ambassadors/HostAmbassadorsNav";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchHostConversions,
  fetchHostDomainPayouts,
  setHostConversionRewardStatus,
  type DomainPayout,
  type HostConversionRow,
} from "@/lib/ambassadors-api";
import { formatDateTime, formatNgn } from "@/lib/format";
import { hasHostPermission } from "@/lib/host-access";

export default function HostAmbassadorPayoutsPage() {
  const { active } = useHostWorkspace();
  const hostId = active?.host_id ?? null;
  const canView = hasHostPermission(
    active,
    "ambassadors.view_payouts",
    "finance.view_payouts",
    "finance.manage_payouts",
  );
  const canMarkPaid = hasHostPermission(
    active,
    "ambassadors.mark_rewards_paid",
    "finance.manage_payouts",
  );

  const [payouts, setPayouts] = useState<DomainPayout[] | null>(null);
  const [payable, setPayable] = useState<HostConversionRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const summary = useMemo(() => {
    const approvedTotal =
      payable?.reduce(
        (sum, row) => sum + Number(row.commission_owed || 0),
        0,
      ) ?? 0;
    const paidTotal =
      payouts
        ?.filter((p) => p.status === "paid" || p.status === "completed")
        .reduce((sum, row) => sum + Number(row.amount || 0), 0) ?? 0;
    return { approvedTotal, paidTotal, payoutCount: payouts?.length ?? 0 };
  }, [payable, payouts]);

  async function load() {
    const [payoutRows, approvedRows] = await Promise.all([
      fetchHostDomainPayouts(hostId),
      fetchHostConversions({ hostId, status: "approved" }),
    ]);
    setPayouts(payoutRows);
    setPayable(approvedRows);
  }

  useEffect(() => {
    if (!hostId && !active?.is_owner) return;
    if (!canView && !active?.is_owner) return;
    let alive = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load payouts",
          );
          setPayouts([]);
          setPayable([]);
        }
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hostId, canView]);

  async function markPaid(row: HostConversionRow) {
    const payout_reference =
      window.prompt("Payout reference (optional)") || null;
    const payout_note = window.prompt("Payout note (optional)") || null;
    setBusy(true);
    setError(null);
    try {
      await setHostConversionRewardStatus(row.id, {
        status: "paid",
        payout_reference,
        payout_note,
        hostId,
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Mark paid failed");
    } finally {
      setBusy(false);
    }
  }

  if (!canView && !active?.is_owner) {
    return (
      <DashboardShell
        tone="soft"
        eyebrow="Ambassador Campaigns"
        title="Payouts & rewards"
        description="View Ambassador payout history and mark approved rewards paid."
      >
        <HostAmbassadorsNav />
        <Alert tone="danger" title="Permission denied">
          You do not have permission to view Ambassador payouts for this host
          workspace.
        </Alert>
      </DashboardShell>
    );
  }

  const loaded = payouts !== null && payable !== null;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Ambassador Campaigns"
      title="Payouts & rewards"
      description={
        canMarkPaid
          ? "Review payout records and mark approved conversion rewards as paid."
          : "View Ambassador payout records. Mark-paid actions require reward or finance payout permissions."
      }
    >
      <HostAmbassadorsNav />
      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}

      {!canMarkPaid && !active?.is_owner ? (
        <Alert tone="info" title="Read-only access">
          You can view payouts but cannot mark rewards paid.
        </Alert>
      ) : null}

      {!loaded ? (
        <SkeletonLoader lines={4} />
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard
              title="Approved (payable)"
              value={formatNgn(summary.approvedTotal)}
            />
            <StatCard title="Paid (records)" value={formatNgn(summary.paidTotal)} />
            <StatCard title="Payout records" value={summary.payoutCount} />
          </div>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-foreground">
              Payable rewards
            </h2>
            <p className="text-sm text-muted-foreground">
              Approved conversions ready to mark paid. Approve rewards on the
              Conversions tab first if needed.
            </p>
            {payable.length === 0 ? (
              <EmptyState
                title="Nothing payable"
                description="Approved conversions ready for payout appear here."
              />
            ) : (
              payable.map((row) => (
                <Card
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-3 p-4"
                >
                  <div>
                    <p className="font-semibold text-foreground">
                      {row.ambassador_display_name || "Ambassador"} ·{" "}
                      {formatNgn(Number(row.commission_owed))}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {row.event_title || row.event_id} ·{" "}
                      {row.ambassador_referral_code}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="accent">approved</Badge>
                    {canMarkPaid ? (
                      <Button disabled={busy} onClick={() => void markPaid(row)}>
                        Mark paid
                      </Button>
                    ) : (
                      <Badge tone="neutral">Read-only</Badge>
                    )}
                  </div>
                </Card>
              ))
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-foreground">
              Payout records
            </h2>
            {payouts.length === 0 ? (
              <EmptyState
                title="No payout records"
                description="Ambassador payout records for this host appear here when available."
              />
            ) : (
              payouts.map((row) => (
                <Card key={row.id} className="space-y-1 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-foreground">
                        {row.display_name || "Ambassador"} ·{" "}
                        {formatNgn(Number(row.amount))}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {row.payout_method || "manual"} ·{" "}
                        {formatDateTime(row.created_at)}
                      </p>
                      {row.notes ? (
                        <p className="mt-1 text-sm text-muted-foreground">
                          {row.notes}
                        </p>
                      ) : null}
                    </div>
                    <Badge
                      tone={
                        row.status === "paid" || row.status === "completed"
                          ? "success"
                          : "neutral"
                      }
                    >
                      {row.status}
                    </Badge>
                  </div>
                </Card>
              ))
            )}
          </section>
        </div>
      )}
    </DashboardShell>
  );
}
