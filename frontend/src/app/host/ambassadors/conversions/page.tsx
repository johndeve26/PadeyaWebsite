"use client";

import { useEffect, useState } from "react";

import { HostAmbassadorsNav } from "@/components/ambassadors/HostAmbassadorsNav";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Select,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchHostConversionAudit,
  fetchHostConversions,
  reverseHostConversion,
  setHostConversionRewardStatus,
  type HostConversionAuditEntry,
  type HostConversionRow,
} from "@/lib/ambassadors-api";
import { formatDateTime, formatNgn } from "@/lib/format";
import { hasHostPermission } from "@/lib/host-access";

type AuditState = {
  loading: boolean;
  error: string | null;
  rows: HostConversionAuditEntry[] | null;
  open: boolean;
};

export default function HostAmbassadorConversionsPage() {
  const { active } = useHostWorkspace();
  const hostId = active?.host_id ?? null;
  const canApprove = hasHostPermission(active, "ambassadors.approve_rewards");
  const canReject = hasHostPermission(
    active,
    "ambassadors.approve_rewards",
    "ambassadors.reject_rewards",
  );
  const canMarkPaid = hasHostPermission(
    active,
    "ambassadors.mark_rewards_paid",
    "finance.manage_payouts",
  );
  const canReverse = hasHostPermission(active, "ambassadors.reverse_rewards");
  const canAnyAction = canApprove || canReject || canMarkPaid || canReverse;

  const [rows, setRows] = useState<HostConversionRow[] | null>(null);
  const [status, setStatus] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [auditById, setAuditById] = useState<Record<string, AuditState>>({});

  async function load(nextStatus = status) {
    setRows(
      await fetchHostConversions({
        hostId,
        status: nextStatus === "all" ? undefined : nextStatus,
      }),
    );
  }

  useEffect(() => {
    if (!hostId && !active?.is_owner) return;
    let alive = true;
    void (async () => {
      try {
        await load("all");
      } catch (err) {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load conversions",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hostId]);

  async function act(
    fn: () => Promise<unknown>,
    failLabel: string,
  ): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : failLabel);
    } finally {
      setBusy(false);
    }
  }

  async function toggleAudit(conversionId: string) {
    const current = auditById[conversionId];
    if (current?.open) {
      setAuditById((prev) => ({
        ...prev,
        [conversionId]: { ...current, open: false },
      }));
      return;
    }

    setAuditById((prev) => ({
      ...prev,
      [conversionId]: {
        loading: true,
        error: null,
        rows: null,
        open: true,
      },
    }));

    try {
      const auditRows = await fetchHostConversionAudit(conversionId, hostId);
      setAuditById((prev) => ({
        ...prev,
        [conversionId]: {
          loading: false,
          error: null,
          rows: auditRows,
          open: true,
        },
      }));
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.status === 404
            ? "Audit history is not available yet."
            : err.detail
          : "Failed to load audit history";
      setAuditById((prev) => ({
        ...prev,
        [conversionId]: {
          loading: false,
          error: message,
          rows: null,
          open: true,
        },
      }));
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Ambassador Campaigns"
      title="Conversions & rewards"
      description={
        canAnyAction
          ? "Approve, reject, mark paid, or reverse Ambassador rewards for your host-owned campaigns."
          : "View Ambassador conversion and reward status. You do not have permission to change reward status."
      }
    >
      <HostAmbassadorsNav />
      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}

      {!canAnyAction && !active?.is_owner ? (
        <Alert tone="info" title="Read-only access">
          Reward approval actions are hidden. Ask the host owner to grant
          Ambassador reward permissions if you need to approve or mark rewards
          paid.
        </Alert>
      ) : null}

      <div className="mb-4 max-w-xs">
        <Select
          label="Status"
          value={status}
          onChange={(e) => {
            const next = e.target.value;
            setStatus(next);
            void load(next).catch((err) => {
              setError(err instanceof ApiError ? err.detail : "Filter failed");
            });
          }}
        >
          <option value="all">All</option>
          <option value="attributed">Attributed</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="paid">Paid</option>
          <option value="reversed">Reversed</option>
        </Select>
      </div>

      {rows === null ? (
        <SkeletonLoader lines={4} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No conversions"
          description="Verified paid referrals for your Ambassadors appear here."
        />
      ) : (
        <div className="space-y-3">
          {rows.map((row) => {
            const audit = auditById[row.id];
            return (
              <Card key={row.id} className="space-y-2 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-foreground">
                      {row.ambassador_display_name || "Ambassador"}{" "}
                      <span className="font-mono text-sm text-muted-foreground">
                        {row.ambassador_referral_code}
                      </span>
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {row.event_title || row.event_id} · {row.tickets_sold}{" "}
                      tickets · {formatNgn(Number(row.revenue_amount))} ·
                      commission {formatNgn(Number(row.commission_owed))}
                    </p>
                    {row.reversal_reason ? (
                      <p className="mt-1 text-sm text-danger-foreground">
                        Reversed: {row.reversal_reason}
                      </p>
                    ) : null}
                    {row.rejection_reason ? (
                      <p className="mt-1 text-sm text-muted-foreground">
                        Rejection reason: {row.rejection_reason}
                      </p>
                    ) : null}
                    {row.payout_reference ? (
                      <p className="mt-1 text-sm text-muted-foreground">
                        Payout reference: {row.payout_reference}
                      </p>
                    ) : null}
                    {row.payout_note ? (
                      <p className="mt-1 text-sm text-muted-foreground">
                        Payout note: {row.payout_note}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {!canAnyAction ? (
                      <Badge tone="neutral">Read-only</Badge>
                    ) : null}
                    <Badge
                      tone={
                        row.status === "reversed" || row.status === "rejected"
                          ? "warning"
                          : row.status === "paid"
                            ? "success"
                            : "neutral"
                      }
                    >
                      {row.status}
                    </Badge>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {row.status === "attributed" && canApprove ? (
                    <Button
                      disabled={busy}
                      onClick={() =>
                        void act(
                          () =>
                            setHostConversionRewardStatus(row.id, {
                              status: "approved",
                              hostId,
                            }),
                          "Approve failed",
                        )
                      }
                    >
                      Approve
                    </Button>
                  ) : null}
                  {(row.status === "attributed" || row.status === "approved") &&
                  canReject ? (
                    <Button
                      disabled={busy}
                      variant="secondary"
                      onClick={() => {
                        const reason = window.prompt(
                          "Reason for rejecting this reward?",
                        );
                        if (!reason || reason.trim().length < 3) return;
                        void act(
                          () =>
                            setHostConversionRewardStatus(row.id, {
                              status: "rejected",
                              reason: reason.trim(),
                              hostId,
                            }),
                          "Reject failed",
                        );
                      }}
                    >
                      Reject
                    </Button>
                  ) : null}
                  {row.status === "approved" && canMarkPaid ? (
                    <Button
                      disabled={busy}
                      onClick={() => {
                        const payout_reference =
                          window.prompt("Payout reference (optional)") || null;
                        const payout_note =
                          window.prompt("Payout note (optional)") || null;
                        void act(
                          () =>
                            setHostConversionRewardStatus(row.id, {
                              status: "paid",
                              payout_reference,
                              payout_note,
                              hostId,
                            }),
                          "Mark paid failed",
                        );
                      }}
                    >
                      Mark paid
                    </Button>
                  ) : null}
                  {row.status !== "reversed" &&
                  row.status !== "paid" &&
                  canReverse ? (
                    <Button
                      disabled={busy}
                      variant="secondary"
                      onClick={() => {
                        const reason = window.prompt(
                          "Reason for reversing this conversion?",
                        );
                        if (!reason || reason.trim().length < 3) return;
                        void act(
                          () =>
                            reverseHostConversion(
                              row.id,
                              reason.trim(),
                              hostId,
                            ),
                          "Reverse failed",
                        );
                      }}
                    >
                      Reverse
                    </Button>
                  ) : null}
                  <Button
                    disabled={busy}
                    size="sm"
                    variant="ghost"
                    onClick={() => void toggleAudit(row.id)}
                  >
                    {audit?.open ? "Hide audit history" : "View audit history"}
                  </Button>
                </div>
                {audit?.open ? (
                  <div className="rounded-md border border-border bg-muted/30 p-3">
                    {audit.loading ? (
                      <SkeletonLoader lines={2} />
                    ) : audit.error ? (
                      <p className="text-sm text-muted-foreground">
                        {audit.error}
                      </p>
                    ) : audit.rows && audit.rows.length > 0 ? (
                      <ul className="space-y-2 text-sm">
                        {audit.rows.map((entry) => {
                          const when =
                            entry.timestamp || entry.created_at || "";
                          const actor =
                            entry.actor_type?.replaceAll("_", " ") ||
                            "actor";
                          const statusLine =
                            entry.old_status && entry.new_status
                              ? `${entry.old_status} → ${entry.new_status}`
                              : null;
                          return (
                            <li
                              key={entry.id}
                              className="border-b border-border pb-2 last:border-0 last:pb-0"
                            >
                              <span className="font-medium text-foreground">
                                {entry.action}
                              </span>
                              <span className="text-muted-foreground">
                                {" "}
                                · {actor}
                                {statusLine ? ` · ${statusLine}` : ""}
                                {when ? ` · ${formatDateTime(when)}` : ""}
                              </span>
                              {entry.reason ? (
                                <p className="mt-0.5 text-muted-foreground">
                                  Reason: {entry.reason}
                                </p>
                              ) : null}
                              {entry.payout_reference ? (
                                <p className="mt-0.5 text-muted-foreground">
                                  Payout ref: {entry.payout_reference}
                                </p>
                              ) : null}
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        No audit entries for this conversion yet.
                      </p>
                    )}
                  </div>
                ) : null}
              </Card>
            );
          })}
        </div>
      )}
    </DashboardShell>
  );
}
