import Link from "next/link";

import { cn } from "@/lib/cn";

import { Badge } from "./Badge";
import { Card } from "./Card";
import { LegacyTierBadge } from "./LegacyTierBadge";
import { Media } from "./Media";

export type HostCardProps = {
  displayName: string;
  username: string;
  bio?: string | null;
  city?: string | null;
  avatarUrl?: string | null;
  verified?: boolean;
  tier?: string | null;
  href?: string;
  className?: string;
};

export function HostCard({
  displayName,
  username,
  bio,
  city,
  avatarUrl,
  verified,
  tier,
  href,
  className = "",
}: HostCardProps) {
  const to = href ?? `/@${username.replace(/^@/, "")}`;

  return (
    <Link href={to} className={cn("group block h-full", className)}>
      <Card hover padded className="h-full space-y-4">
        <div className="flex items-center gap-3">
          <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-full border border-border bg-surface-dark">
            {avatarUrl ? (
              <Media src={avatarUrl} />
            ) : (
              <span className="flex h-full w-full items-center justify-center text-lg font-extrabold text-primary">
                {displayName.slice(0, 1).toUpperCase()}
              </span>
            )}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="truncate text-base font-bold text-foreground">
                {displayName}
              </h3>
              {verified ? <Badge tone="accent">Verified</Badge> : null}
            </div>
            <p className="text-sm text-muted-foreground">@{username.replace(/^@/, "")}</p>
          </div>
        </div>
        {tier ? <LegacyTierBadge tier={tier} /> : null}
        {bio ? (
          <p className="line-clamp-3 text-sm leading-relaxed text-muted-foreground">
            {bio}
          </p>
        ) : null}
        {city ? (
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
            {city}
          </p>
        ) : null}
      </Card>
    </Link>
  );
}
