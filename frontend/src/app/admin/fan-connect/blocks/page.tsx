"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAdminFanConnectBlocks } from "@/lib/fan-connect-api";
import type { FanConnectAdminBlock } from "@/lib/types/fan-connect";
import { formatDate } from "@/lib/format";

export default function AdminFanConnectBlocksPage() {
  const [items, setItems] = useState<FanConnectAdminBlock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetchAdminFanConnectBlocks();
        if (!active) return;
        setItems(res.items);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError ? err.detail : "Could not load blocks.",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Fan Connect"
      title="Blocks"
      description="Privacy-safe block list (display names only — no emails or phones)."
      actions={
        <Link href="/admin/fan-connect">
          <Button variant="secondary">Back</Button>
        </Link>
      }
    >
      {loading ? <SkeletonLoader className="h-32" /> : null}
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title="No blocks"
          description="User blocks that affect messaging and Connect appear here."
        />
      ) : null}
      {items.length > 0 ? (
        <ul className="divide-y divide-border rounded-[var(--radius-lg)] border border-border bg-surface">
          {items.map((row) => (
            <li key={row.id} className="space-y-1 px-4 py-4 sm:px-5">
              <p className="font-semibold text-ink">
                {row.blocker_display_name}
                {row.blocker_username ? (
                  <span className="font-normal text-muted">
                    {" "}
                    @{row.blocker_username}
                  </span>
                ) : null}{" "}
                blocked {row.blocked_display_name}
                {row.blocked_username ? (
                  <span className="font-normal text-muted">
                    {" "}
                    @{row.blocked_username}
                  </span>
                ) : null}
              </p>
              {row.reason ? (
                <p className="text-sm text-muted">{row.reason}</p>
              ) : null}
              <p className="text-xs text-muted">{formatDate(row.created_at)}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </DashboardShell>
  );
}
