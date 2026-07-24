"use client";

import Link from "next/link";

import { Badge, Button, Media } from "@/components/ui";
import type { LegacyPage } from "@/lib/types/legacy";

type Props = {
  username: string;
  legacy: LegacyPage | null;
  following: boolean;
  followBusy: boolean;
  onFollow: () => void;
};

export function VaultItemHostCard({
  username,
  legacy,
  following,
  followBusy,
  onFollow,
}: Props) {
  const displayName = legacy?.display_name || username;
  const avatarUrl = legacy?.profile?.avatar_url || null;

  return (
    <aside className="overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)] dark:bg-surface-elevated dark:shadow-[var(--shadow)]">
      <div className="border-b border-border bg-muted/70 px-5 py-3">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Host
        </p>
      </div>
      <div className="space-y-4 p-5">
        <div className="flex items-center gap-3">
          <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-full bg-ink">
            {avatarUrl ? (
              <Media src={avatarUrl} alt="" className="h-full w-full object-cover" />
            ) : (
              <span className="flex h-full w-full items-center justify-center text-lg font-extrabold text-accent">
                {displayName.slice(0, 1).toUpperCase()}
              </span>
            )}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="truncate text-lg font-extrabold text-foreground">
                {displayName}
              </p>
              {legacy?.verified ? <Badge tone="accent">Verified</Badge> : null}
            </div>
            <p className="text-sm text-muted-foreground">@{username}</p>
          </div>
        </div>
        {legacy?.tagline || legacy?.about ? (
          <p className="line-clamp-3 text-sm leading-relaxed text-muted-foreground">
            {legacy.tagline || legacy.about}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          {legacy?.follow_enabled !== false ? (
            <Button
              size="sm"
              variant={following ? "secondary" : "primary"}
              disabled={followBusy || !legacy?.host_id}
              onClick={onFollow}
            >
              {following ? "Following" : "Follow host"}
            </Button>
          ) : null}
          <Link href={`/u/${username}`}>
            <Button size="sm" variant="secondary">
              Legacy Page
            </Button>
          </Link>
          <Link href={`/u/${username}/vault`}>
            <Button size="sm" variant="ghost">
              All Vault drops
            </Button>
          </Link>
        </div>
      </div>
    </aside>
  );
}
