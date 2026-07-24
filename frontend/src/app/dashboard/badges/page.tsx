"use client";

import Link from "next/link";
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
import { cn } from "@/lib/cn";
import { formatDate } from "@/lib/format";
import { fetchMyBadges } from "@/lib/passport-api";
import type { FanBadge } from "@/lib/types/passport";

export default function BadgesPage() {
  const [badges, setBadges] = useState<FanBadge[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const rows = await fetchMyBadges();
        if (active) setBadges(rows);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load badges");
        }
      } finally {
        if (active) setLoaded(true);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const earned = badges.filter((b) => b.earned).length;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Fan Passport"
      title="Badge collection"
      description={`${earned} of ${badges.length} earned. Awards are deterministic from your tickets and check-ins.`}
      actions={
        <Link href="/dashboard/passport">
          <Button variant="secondary">Back to Passport</Button>
        </Link>
      }
    >
      {error ? (
        <Alert tone="danger" title="Could not load badges">
          {error}
        </Alert>
      ) : null}

      {!loaded && !error ? <SkeletonLoader lines={4} /> : null}

      {loaded && badges.length > 0 ? (
        <Card variant="dark" className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">
            Progress
          </p>
          <p className="text-3xl font-extrabold text-paper">
            {earned}
            <span className="text-lg font-semibold text-subtle-foreground">
              {" "}
              / {badges.length}
            </span>
          </p>
          <div className="h-2 overflow-hidden rounded-full bg-paper/10">
            <div
              className="h-full rounded-full bg-accent transition-all"
              style={{
                width: `${badges.length ? Math.round((earned / badges.length) * 100) : 0}%`,
              }}
            />
          </div>
        </Card>
      ) : null}

      {loaded && badges.length === 0 && !error ? (
        <EmptyState
          title="No badges in catalog yet"
          description="Check back after you’ve attended nights on Pàdéyá."
        />
      ) : loaded && badges.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {badges.map((b) => (
            <Card
              key={b.id}
              className={cn(
                "relative space-y-4 overflow-hidden",
                b.earned
                  ? "border-primary/50 shadow-[var(--shadow-glow)]"
                  : "bg-surface-inset",
              )}
            >
              <div
                className={cn(
                  "flex h-14 w-14 items-center justify-center rounded-full text-sm font-extrabold uppercase tracking-wide",
                  b.earned
                    ? "bg-ink text-primary"
                    : "bg-surface-muted text-muted-foreground",
                )}
              >
                {(b.name || "??").slice(0, 2)}
              </div>
              <div className="flex items-start justify-between gap-2">
                <h3
                  className={cn(
                    "text-lg font-extrabold",
                    b.earned ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  {b.name}
                </h3>
                <Badge tone={b.earned ? "accent" : "neutral"}>
                  {b.earned ? "Earned" : "Locked"}
                </Badge>
              </div>
              <p
                className={cn(
                  "text-base leading-relaxed",
                  b.earned ? "text-muted-foreground" : "text-muted-foreground/80",
                )}
              >
                {b.description}
              </p>
              {b.awarded_at ? (
                <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                  Earned {formatDate(b.awarded_at)}
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Keep checking in to unlock.
                </p>
              )}
            </Card>
          ))}
        </div>
      ) : null}
    </DashboardShell>
  );
}
