"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchMyFollowing,
  unfollowHost,
  updateMarketingOptIn,
} from "@/lib/crm-api";
import type { FollowingHost } from "@/lib/types/crm";

export default function FollowingPage() {
  const [rows, setRows] = useState<FollowingHost[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  async function load() {
    setRows(await fetchMyFollowing());
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load following");
        }
      } finally {
        if (active) setLoaded(true);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onToggleOptIn(host: FollowingHost) {
    setError(null);
    try {
      await updateMarketingOptIn(host.host_id, !host.marketing_opt_in);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    }
  }

  async function onUnfollow(hostId: string) {
    setError(null);
    try {
      await unfollowHost(hostId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Unfollow failed");
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Following"
      title="Hosts you follow"
      description="Following a host does not email you automatically. Turn on Notify for hosts you want event updates from."
      actions={
        <Link href="/hosts">
          <Button variant="primary">Find hosts</Button>
        </Link>
      }
    >
      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}

      {!loaded && !error ? <SkeletonLoader lines={4} /> : null}

      {loaded && rows.length === 0 ? (
        <EmptyState
          title="You’re not following anyone yet"
          description="Visit a Legacy Page and follow hosts you want to stay close to."
          action={
            <Link href="/hosts">
              <Button size="lg">Browse hosts</Button>
            </Link>
          }
        />
      ) : loaded ? (
        <div className="space-y-3">
          {rows.map((h) => (
            <div
              key={h.host_id}
              className="flex flex-wrap items-center justify-between gap-4 rounded-[var(--radius-lg)] border border-border bg-card px-4 py-4 shadow-[var(--shadow-soft)] dark:bg-surface-elevated"
            >
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-ink text-sm font-extrabold text-accent">
                  {(h.display_name || "?").slice(0, 1).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <Link
                    href={`/@${h.username}`}
                    className="text-base font-extrabold text-foreground hover:underline"
                  >
                    {h.display_name}
                  </Link>
                  <p className="text-sm text-muted-foreground">@{h.username}</p>
                  {h.marketing_opt_in ? (
                    <Badge tone="accent" className="mt-1">
                      Email notifications on
                    </Badge>
                  ) : (
                    <p className="mt-1 text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                      Email notifications off
                    </p>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant={h.marketing_opt_in ? "secondary" : "primary"}
                  onClick={() => void onToggleOptIn(h)}
                >
                  {h.marketing_opt_in ? "Mute email updates" : "Notify me by email"}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => void onUnfollow(h.host_id)}
                >
                  Unfollow
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </DashboardShell>
  );
}
