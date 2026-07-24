"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  disableAdminFanConnectUser,
  fetchAdminFanConnectUserHistory,
} from "@/lib/fan-connect-api";
import type { FanConnectAdminUserHistory } from "@/lib/types/fan-connect";
import { formatDate } from "@/lib/format";

export default function AdminFanConnectUserHistoryPage() {
  const params = useParams<{ userId: string }>();
  const [data, setData] = useState<FanConnectAdminUserHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!params?.userId) return;
    let active = true;
    void (async () => {
      try {
        const history = await fetchAdminFanConnectUserHistory(params.userId);
        if (!active) return;
        setData(history);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError ? err.detail : "Could not load history.",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [params?.userId]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Fan Connect"
      title={data?.display_name || "User moderation"}
      description="Block and report history for this fan. No emails, phones, orders, or payments."
      actions={
        <Link href="/admin/fan-connect/reports">
          <Button variant="secondary">Back to reports</Button>
        </Link>
      }
    >
      {loading ? <SkeletonLoader className="h-32" /> : null}
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {data ? (
        <div className="space-y-6">
          <Card className="flex flex-wrap items-center justify-between gap-3 p-5">
            <div>
              <p className="font-extrabold text-ink">
                {data.display_name}
                {data.username ? (
                  <span className="font-normal text-muted">
                    {" "}
                    @{data.username}
                  </span>
                ) : null}
              </p>
              <p className="mt-1 text-sm text-muted">
                Fan Connect:{" "}
                {data.fan_connect_enabled ? "enabled" : "disabled"}
              </p>
            </div>
            {data.fan_connect_enabled ? (
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => {
                  setBusy(true);
                  void disableAdminFanConnectUser(data.user_id, {
                    reason: "Disabled from moderation history",
                  })
                    .then(() =>
                      fetchAdminFanConnectUserHistory(data.user_id).then(
                        setData,
                      ),
                    )
                    .catch((err) =>
                      setError(
                        err instanceof ApiError
                          ? err.detail
                          : "Could not disable.",
                      ),
                    )
                    .finally(() => setBusy(false));
                }}
              >
                Disable Fan Connect
              </Button>
            ) : (
              <Badge tone="neutral">Connect off</Badge>
            )}
          </Card>

          <section className="space-y-3">
            <h2 className="text-lg font-extrabold text-ink">
              Reports about this fan
            </h2>
            {data.reports_about.length === 0 ? (
              <EmptyState
                title="No reports"
                description="Nobody has filed a Fan Connect report about this fan."
              />
            ) : (
              <ul className="divide-y divide-border rounded-[var(--radius-lg)] border border-border bg-surface">
                {data.reports_about.map((r) => (
                  <li key={r.id} className="px-4 py-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold">{r.reason}</span>
                      <Badge tone="outline" size="sm">
                        {r.status}
                      </Badge>
                    </div>
                    <p className="mt-1 text-muted">
                      by {r.reporter_display_name} · {formatDate(r.created_at)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-extrabold text-ink">
              Reports filed by this fan
            </h2>
            {data.reports_filed.length === 0 ? (
              <EmptyState
                title="None filed"
                description="This fan has not filed Fan Connect reports."
              />
            ) : (
              <ul className="divide-y divide-border rounded-[var(--radius-lg)] border border-border bg-surface">
                {data.reports_filed.map((r) => (
                  <li key={r.id} className="px-4 py-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold">{r.reason}</span>
                      <Badge tone="outline" size="sm">
                        {r.status}
                      </Badge>
                    </div>
                    <p className="mt-1 text-muted">
                      about {r.reported_display_name} ·{" "}
                      {formatDate(r.created_at)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-extrabold text-ink">Blocks</h2>
            {data.blocks_as_blocker.length === 0 &&
            data.blocks_as_blocked.length === 0 ? (
              <EmptyState
                title="No blocks"
                description="No Fan Connect blocks involve this fan."
              />
            ) : (
              <ul className="divide-y divide-border rounded-[var(--radius-lg)] border border-border bg-surface">
                {data.blocks_as_blocker.map((b) => (
                  <li key={`blocker-${b.id}`} className="px-4 py-3 text-sm">
                    Blocked {b.blocked_display_name}
                    {b.blocked_username ? ` (@${b.blocked_username})` : ""}
                    <span className="block text-xs text-muted">
                      {formatDate(b.created_at)}
                    </span>
                  </li>
                ))}
                {data.blocks_as_blocked.map((b) => (
                  <li key={`blocked-${b.id}`} className="px-4 py-3 text-sm">
                    Blocked by {b.blocker_display_name}
                    {b.blocker_username ? ` (@${b.blocker_username})` : ""}
                    <span className="block text-xs text-muted">
                      {formatDate(b.created_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      ) : null}
    </DashboardShell>
  );
}
