"use client";

import Link from "next/link";

import { Badge, Button, StatusBadge } from "@/components/ui";
import type { Host } from "@/lib/types/events";
import type { LegacyPage } from "@/lib/types/legacy";

/**
 * Owner Command Center page header.
 * Shell already shows `Host: {name}` — do not repeat it as H1.
 * Workspace switching stays in the shell toolbar only.
 */
export function CommandCenterHeader({
  host,
  legacy,
}: {
  host: Host | null;
  legacy: LegacyPage | null;
}) {
  const location =
    [host?.profile?.city, host?.profile?.state, host?.profile?.country]
      .filter(Boolean)
      .join(", ") || null;
  const bio = host?.profile?.bio?.trim() || null;

  return (
    <section className="rounded-[var(--radius-lg)] border border-border bg-card px-4 py-4 shadow-[var(--shadow-soft)] dark:bg-surface-elevated">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">
            Host Command Center
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-bold text-foreground sm:text-2xl">
              Overview
            </h1>
            {legacy?.verified ? (
              <Badge tone="success">Verified</Badge>
            ) : (
              <Badge tone="warning">Unverified</Badge>
            )}
            {host?.status ? <StatusBadge status={host.status} /> : null}
          </div>
          <p className="max-w-2xl text-base leading-relaxed text-muted-foreground">
            Run today&apos;s ops, clear setup gaps, and jump into events from one
            place.
          </p>
          {bio || location ? (
            <div className="space-y-1 text-sm text-muted-foreground">
              {bio ? <p>{bio}</p> : null}
              {location ? <p>{location}</p> : null}
            </div>
          ) : null}
          <div className="flex flex-wrap gap-2 pt-1">
            <Link href="/host/settings">
              <Button size="sm" variant="secondary">
                Edit profile
              </Button>
            </Link>
            <Link href="/host/legacy">
              <Button size="sm" variant="secondary">
                Legacy Page
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
