"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DeclineRequestModal } from "@/components/fan-connect/DeclineRequestModal";
import { SharedContextChips } from "@/components/fan-connect/SharedContextChips";
import { GenderBadge } from "@/components/profile/GenderBadge";
import {
  Alert,
  Button,
  EmptyState,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  acceptConnectRequest,
  cancelConnectRequest,
  declineConnectRequest,
  fetchConnectRequests,
} from "@/lib/fan-connect-api";
import type { FanConnection } from "@/lib/types/fan-connect";

type Props = {
  box: "incoming" | "outgoing";
};

export function ConnectRequestList({ box }: Props) {
  const toast = useToast();
  const router = useRouter();
  const [items, setItems] = useState<FanConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [declineTargetId, setDeclineTargetId] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchConnectRequests(box);
        if (!active) return;
        setItems(data.items);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError ? err.detail : "Could not load requests.",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [box, tick]);

  async function run(id: string, action: () => Promise<FanConnection>) {
    setBusyId(id);
    setError(null);
    try {
      const row = await action();
      setTick((n) => n + 1);
      if (row.status === "connected" && row.thread_id) {
        toast.push({
          tone: "success",
          title: "Connected — opening messages",
        });
        router.push(`/dashboard/messages/${row.thread_id}`);
        return;
      }
      toast.push({
        tone: "success",
        title: box === "incoming" ? "Updated" : "Request updated",
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Action failed.");
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <SkeletonLoader className="h-32" />;
  if (error) return <Alert tone="danger">{error}</Alert>;
  if (items.length === 0) {
    return (
      <EmptyState
        title={
          box === "incoming" ? "No incoming requests" : "No outgoing requests"
        }
        description="Connect when you share a public night, host, or scene on Pàdéyá."
      />
    );
  }

  return (
    <>
      <DeclineRequestModal
        open={declineTargetId != null}
        onClose={() => setDeclineTargetId(null)}
        busy={busyId != null}
        onConfirm={async (cooldownDays) => {
          if (!declineTargetId) return;
          await run(declineTargetId, () =>
            declineConnectRequest(declineTargetId, {
              cooldown_days: cooldownDays,
            }),
          );
          setDeclineTargetId(null);
        }}
      />
      <ul className="divide-y divide-border rounded-[var(--radius-lg)] border border-border bg-card dark:bg-surface-elevated">
      {items.map((row) => {
        const name = row.counterpart.display_name;
        const uname = row.counterpart.username;
        return (
          <li key={row.id} className="space-y-3 px-4 py-4 sm:px-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-heading">{name}</p>
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
                {row.message ? (
                  <p className="mt-2 text-sm text-foreground/80">
                    &ldquo;{row.message}&rdquo;
                  </p>
                ) : null}
              </div>
              <div className="flex flex-wrap gap-2">
                {box === "incoming" ? (
                  <>
                    <Button
                      size="sm"
                      disabled={busyId === row.id}
                      onClick={() =>
                        void run(row.id, () => acceptConnectRequest(row.id))
                      }
                    >
                      Accept
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={busyId === row.id}
                      onClick={() => setDeclineTargetId(row.id)}
                    >
                      Decline
                    </Button>
                  </>
                ) : (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={busyId === row.id}
                    onClick={() =>
                      void run(row.id, () => cancelConnectRequest(row.id))
                    }
                  >
                    Cancel
                  </Button>
                )}
              </div>
            </div>
            {row.shared_context ? (
              <SharedContextChips context={row.shared_context} />
            ) : null}
          </li>
        );
      })}
    </ul>
    </>
  );
}
