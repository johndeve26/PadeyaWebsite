"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { SharedContextChips } from "@/components/fan-connect/SharedContextChips";
import { GenderBadge } from "@/components/profile/GenderBadge";
import {
  Alert,
  Button,
  EmptyState,
  Modal,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  blockFanConnect,
  fetchConnections,
  removeConnection,
  reportFanConnect,
} from "@/lib/fan-connect-api";
import {
  formatSelfBlockError,
  formatSelfReportError,
} from "@/lib/messaging-errors";
import { isOwnFanPassport } from "@/lib/own-fan-ctas";
import type { FanConnection } from "@/lib/types/fan-connect";

export function ConnectionsList() {
  const { user } = useAuth();
  const toast = useToast();
  const [items, setItems] = useState<FanConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [reportFor, setReportFor] = useState<FanConnection | null>(null);
  const [reportReason, setReportReason] = useState("");
  const [reportDetails, setReportDetails] = useState("");
  const [reportError, setReportError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchConnections();
        if (!active) return;
        setItems(data.items);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError
            ? err.detail
            : "Could not load connections.",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [tick]);

  if (loading) return <SkeletonLoader className="h-32" />;
  if (error) return <Alert tone="danger">{error}</Alert>;
  if (items.length === 0) {
    return (
      <EmptyState
        title="No connections yet"
        description="When you accept a Fan Connect request, chat unlocks here and in Messages."
      />
    );
  }

  return (
    <>
      <ul className="divide-y divide-border rounded-[var(--radius-lg)] border border-border bg-card dark:bg-surface-elevated">
        {items.map((row) => {
          const uname = row.counterpart.username;
          const isSelf = isOwnFanPassport(user?.id, row.counterpart.user_id);
          return (
            <li key={row.id} className="space-y-3 px-4 py-4 sm:px-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-heading">
                      {row.counterpart.display_name}
                    </p>
                    {row.counterpart.gender_visible &&
                    row.counterpart.gender_short ? (
                      <GenderBadge
                        value={{
                          gender: row.counterpart.gender ?? null,
                          gender_short: row.counterpart.gender_short,
                          gender_label: row.counterpart.gender_label ?? null,
                          gender_visible: row.counterpart.gender_visible,
                        }}
                      />
                    ) : null}
                  </div>
                  {uname ? (
                    <Link
                      href={`/f/${uname}`}
                      className="text-sm text-muted-foreground hover:text-primary"
                    >
                      @{uname}
                    </Link>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2">
                  {row.thread_id && !isSelf ? (
                    <Link href={`/dashboard/messages/${row.thread_id}`}>
                      <Button size="sm">Message</Button>
                    </Link>
                  ) : null}
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={busyId === row.id}
                    onClick={() => {
                      setBusyId(row.id);
                      void removeConnection(row.id)
                        .then(() => {
                          setTick((n) => n + 1);
                          toast.push({
                            tone: "success",
                            title: "Connection removed",
                          });
                        })
                        .catch((err) =>
                          setError(
                            err instanceof ApiError
                              ? err.detail
                              : "Could not remove connection.",
                          ),
                        )
                        .finally(() => setBusyId(null));
                    }}
                  >
                    Remove
                  </Button>
                  {uname && !isSelf ? (
                    <>
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busyId === row.id}
                        onClick={() => {
                          setBusyId(row.id);
                          void blockFanConnect({ username: uname })
                            .then(() => {
                              setTick((n) => n + 1);
                              toast.push({ tone: "success", title: "Blocked" });
                            })
                            .catch((err) =>
                              setError(formatSelfBlockError(err, "Could not block.")),
                            )
                            .finally(() => setBusyId(null));
                        }}
                      >
                        Block
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busyId === row.id}
                        onClick={() => {
                          setReportFor(row);
                          setReportReason("");
                          setReportDetails("");
                          setReportError(null);
                        }}
                      >
                        Report
                      </Button>
                    </>
                  ) : null}
                </div>
              </div>
              {row.shared_context ? (
                <SharedContextChips context={row.shared_context} />
              ) : null}
            </li>
          );
        })}
      </ul>

      <Modal
        open={Boolean(reportFor)}
        onClose={() => setReportFor(null)}
        title="Report fan"
        description="Tell us what’s wrong. Reports stay private to Pàdéyá moderation."
      >
        <div className="space-y-3">
          <input
            value={reportReason}
            onChange={(e) => setReportReason(e.target.value.slice(0, 120))}
            className="w-full rounded-[var(--radius-md)] border border-border bg-background px-3 py-2 text-sm"
            placeholder="Reason (required)"
          />
          <textarea
            value={reportDetails}
            onChange={(e) => setReportDetails(e.target.value.slice(0, 2000))}
            rows={3}
            className="w-full rounded-[var(--radius-md)] border border-border bg-background px-3 py-2 text-sm"
            placeholder="Optional details"
          />
          {reportError ? (
            <p className="text-sm font-semibold text-danger">{reportError}</p>
          ) : null}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setReportFor(null)}>
              Cancel
            </Button>
            <Button
              disabled={
                !reportFor?.counterpart.username ||
                reportReason.trim().length < 3 ||
                busyId === reportFor?.id
              }
              onClick={() => {
                if (!reportFor?.counterpart.username) return;
                setBusyId(reportFor.id);
                setReportError(null);
                void reportFanConnect({
                  username: reportFor.counterpart.username,
                  reason: reportReason.trim(),
                  details: reportDetails.trim() || undefined,
                  connection_id: reportFor.id,
                  thread_id: reportFor.thread_id ?? undefined,
                })
                  .then(() => {
                    setReportFor(null);
                    toast.push({ tone: "success", title: "Report submitted" });
                  })
                  .catch((err) =>
                    setReportError(
                      formatSelfReportError(
                        err,
                        err instanceof ApiError
                          ? err.detail
                          : "Could not submit report.",
                      ),
                    ),
                  )
                  .finally(() => setBusyId(null));
              }}
            >
              Submit report
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
