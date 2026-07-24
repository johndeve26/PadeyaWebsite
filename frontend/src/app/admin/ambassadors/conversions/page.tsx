"use client";

import { useEffect, useState } from "react";

import { AdminAmbassadorsNav } from "@/components/ambassadors/AdminAmbassadorsNav";
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
import { formatNgn } from "@/lib/format";
import {
  fetchAdminConversions,
  reverseAdminConversion,
  setAdminConversionRewardStatus,
} from "@/lib/promos-api";
import type { AmbassadorConversionAdmin } from "@/lib/types/promos";

export default function AdminAmbassadorConversionsPage() {
  const [rows, setRows] = useState<AmbassadorConversionAdmin[] | null>(null);
  const [status, setStatus] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load(nextStatus = status) {
    setRows(
      await fetchAdminConversions(
        nextStatus === "all" ? undefined : { status: nextStatus },
      ),
    );
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load("all");
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load conversions",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onApprove(id: string) {
    setBusy(true);
    setError(null);
    try {
      await setAdminConversionRewardStatus(id, "approved");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Approve failed");
    } finally {
      setBusy(false);
    }
  }

  async function onReject(id: string) {
    setBusy(true);
    setError(null);
    try {
      await setAdminConversionRewardStatus(id, "rejected");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Reject failed");
    } finally {
      setBusy(false);
    }
  }

  async function onReverse(id: string) {
    const reason = window.prompt("Reason for reversing this conversion?");
    if (!reason || reason.trim().length < 3) return;
    setBusy(true);
    setError(null);
    try {
      await reverseAdminConversion(id, reason.trim());
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Reverse failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Ambassadors"
      title="Conversions"
      description="Platform oversight: fraud intervention, support escalation, platform campaigns, and emergency correction. Hosts approve/pay host-owned rewards on /host/ambassadors/conversions — admin.full_access is not required for that normal workflow."
    >
      <AdminAmbassadorsNav />
      {error ? <Alert tone="danger" title="Something went wrong">{error}</Alert> : null}

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="max-w-xs flex-1">
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
            <option value="reversed">Reversed (fraud)</option>
          </Select>
        </div>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            setStatus("reversed");
            void load("reversed").catch((err) => {
              setError(err instanceof ApiError ? err.detail : "Filter failed");
            });
          }}
        >
          Show fraud flags
        </Button>
      </div>

      {rows === null ? (
        <SkeletonLoader lines={4} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No conversions"
          description="Verified paid orders attributed to ambassadors appear here."
        />
      ) : (
        <div className="space-y-3">
          {rows.map((row) => (
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
                    {row.event_title || row.event_id} ·{" "}
                    {row.tickets_sold} tickets · {formatNgn(Number(row.revenue_amount))}{" "}
                    · commission {formatNgn(Number(row.commission_owed))}
                  </p>
                  {row.reversal_reason ? (
                    <p className="mt-1 text-sm text-danger-foreground">
                      Reversed: {row.reversal_reason}
                    </p>
                  ) : null}
                </div>
                <Badge
                  tone={
                    row.status === "reversed"
                      ? "warning"
                      : row.status === "paid"
                        ? "success"
                        : "neutral"
                  }
                >
                  {row.status}
                </Badge>
              </div>
              <div className="flex flex-wrap gap-2">
                {row.status === "attributed" ? (
                  <Button
                    disabled={busy}
                    onClick={() => void onApprove(row.id)}
                  >
                    Approve reward
                  </Button>
                ) : null}
                {row.status === "attributed" || row.status === "approved" ? (
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void onReject(row.id)}
                  >
                    Reject
                  </Button>
                ) : null}
                {row.status !== "reversed" && row.status !== "paid" ? (
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void onReverse(row.id)}
                  >
                    Reverse
                  </Button>
                ) : null}
              </div>
            </Card>
          ))}
        </div>
      )}
    </DashboardShell>
  );
}
