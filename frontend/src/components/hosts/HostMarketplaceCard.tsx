"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { HostFollowControls } from "@/components/hosts/HostFollowControls";
import { GenderBadge } from "@/components/profile/GenderBadge";
import { Badge, Button, Card, LegacyTierBadge, Media } from "@/components/ui";
import { useHostAffiliation } from "@/hooks/useHostAffiliation";
import {
  trackHostCardClick,
  trackHostCardImpression,
  trackHostFollowClick,
} from "@/lib/analytics";
import { cn } from "@/lib/cn";
import {
  formatCompact,
  resolveHostMedia,
} from "@/lib/legacy-presentation";
import type { HostDiscovery } from "@/lib/types/hosts-discovery";

/** @deprecated Featured uses the same card layout as directory. */
export type HostMarketplaceCardVariant = "featured" | "directory";

function categoryLabel(slug: string | null | undefined): string | null {
  if (!slug) return null;
  return slug
    .split("-")
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(" ");
}

function statDisplay(value: string | null): string {
  return value ?? "—";
}

function VerifiedCheckIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 20 20"
      aria-hidden
      className={cn("h-4 w-4 shrink-0 text-primary", className)}
    >
      <path
        fill="currentColor"
        d="M10 1.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17Zm3.78 6.03-4.5 4.5a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 1 1 1.06-1.06l1.47 1.47 3.97-3.97a.75.75 0 1 1 1.06 1.06Z"
      />
    </svg>
  );
}

function StatsStrip({
  upcoming,
  ticketsSold,
  rating,
  upcomingHref,
}: {
  upcoming: string | null;
  ticketsSold: string | null;
  rating: string | null;
  upcomingHref?: string | null;
}) {
  const items = [
    {
      label: "Upcoming",
      value: statDisplay(upcoming),
      href:
        upcoming && upcoming !== "—" && upcomingHref ? upcomingHref : null,
    },
    { label: "Tickets sold", value: statDisplay(ticketsSold), href: null },
    { label: "Rating", value: statDisplay(rating), href: null },
  ];

  return (
    <div className="grid grid-cols-3 gap-2">
      {items.map((item) => {
        const inner = (
          <>
            <p className="text-sm font-bold tabular-nums text-foreground">
              {item.value}
            </p>
            <p className="text-[10px] font-medium text-muted-foreground">
              {item.label}
            </p>
          </>
        );
        return (
          <div
            key={item.label}
            className="rounded-[var(--radius-sm)] border border-border/70 bg-surface/30 px-2 py-1.5 text-center"
          >
            {item.href ? (
              <Link
                href={item.href}
                className="block rounded-sm transition-colors hover:bg-muted/30"
              >
                {inner}
              </Link>
            ) : (
              inner
            )}
          </div>
        );
      })}
    </div>
  );
}

function CapabilityChips({
  sponsorReady,
  vaultActive,
}: {
  sponsorReady: boolean;
  vaultActive: boolean;
}) {
  if (!sponsorReady && !vaultActive) return null;

  return (
    <div className="flex flex-wrap gap-1.5">
      {sponsorReady ? (
        <Badge tone="outline" size="sm" className="font-semibold normal-case tracking-normal">
          Sponsor-ready
        </Badge>
      ) : null}
      {vaultActive ? (
        <Badge tone="accent" size="sm" className="font-semibold normal-case tracking-normal">
          Vault active
        </Badge>
      ) : null}
    </div>
  );
}

export function HostMarketplaceCard({
  host,
  initiallyFollowing = false,
  variant: _variant = "directory",
  className = "",
}: {
  host: HostDiscovery;
  initiallyFollowing?: boolean;
  variant?: HostMarketplaceCardVariant;
  className?: string;
}) {
  const rootRef = useRef<HTMLElement | null>(null);
  const [followError, setFollowError] = useState<string | null>(null);

  const media = resolveHostMedia(
    host.username,
    host.cover_url,
    host.avatar_url,
  );
  const href = host.share_path || `/@${host.username}`;
  const bio = host.tagline || host.bio || "New Legacy Page";
  const category = categoryLabel(host.primary_category || host.host_type);
  const placeLine =
    [category, host.primary_city].filter(Boolean).join(" · ") || "Legacy Page";
  const ticketsSoldCount = host.tickets_sold_count ?? 0;

  const upcoming =
    host.upcoming_events_count > 0
      ? String(host.upcoming_events_count)
      : null;
  const ticketsSold =
    ticketsSoldCount > 0 ? formatCompact(ticketsSoldCount) : null;
  const rating =
    host.average_rating != null ? host.average_rating.toFixed(1) : null;

  const nextEvent = host.next_upcoming_event;
  const eventHref =
    nextEvent?.slug?.trim() ? `/events/${nextEvent.slug}` : null;
  const hostUpcomingHref = `${href}#upcoming-events`;

  const { affiliated: isOwnHost, loading: ownHostLoading } = useHostAffiliation({
    hostId: host.host_id,
    hostSlug: host.username,
  });

  useEffect(() => {
    const el = rootRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting && e.intersectionRatio >= 0.45)) {
          trackHostCardImpression({
            hostId: host.host_id,
            username: host.username,
          });
          obs.disconnect();
        }
      },
      { threshold: [0.45] },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [host.host_id, host.username]);

  return (
    <article ref={rootRef} className={cn("flex h-full flex-col", className)}>
      <Card
        hover
        padded
        className="flex h-full min-h-[18rem] flex-col gap-3 border-border/80 shadow-[var(--shadow-soft)]"
      >
        <div className="flex flex-1 flex-col gap-2.5">
          <div className="flex items-start gap-3.5">
            <Link
              href={href}
              onClick={() =>
                trackHostCardClick({
                  hostId: host.host_id,
                  username: host.username,
                  target: "avatar",
                })
              }
              className="relative h-11 w-11 shrink-0 overflow-hidden rounded-full border border-border/80 bg-surface-dark"
            >
              {media.avatarUrl ? (
                <Media
                  src={media.avatarUrl}
                  alt=""
                  className="h-full w-full object-cover"
                />
              ) : (
                <span className="flex h-full w-full items-center justify-center text-base font-extrabold text-accent">
                  {host.display_name.slice(0, 1).toUpperCase()}
                </span>
              )}
            </Link>
            <div className="min-w-0 flex-1 space-y-1.5">
              <div className="flex min-w-0 items-center gap-1.5">
                <Link
                  href={href}
                  onClick={() =>
                    trackHostCardClick({
                      hostId: host.host_id,
                      username: host.username,
                      target: "name",
                    })
                  }
                  className="truncate text-base font-extrabold tracking-tight text-foreground"
                >
                  {host.display_name}
                </Link>
                {host.verified ? (
                  <span
                    className="inline-flex shrink-0"
                    title="Verified host"
                    aria-label="Verified host"
                  >
                    <VerifiedCheckIcon />
                  </span>
                ) : null}
                {host.shows_personal_gender &&
                host.gender_visible &&
                host.gender_short ? (
                  <GenderBadge
                    value={{
                      gender: host.gender ?? null,
                      gender_short: host.gender_short,
                      gender_label: host.gender_label ?? null,
                      gender_visible: host.gender_visible,
                    }}
                  />
                ) : null}
              </div>
              <p className="text-sm leading-snug text-muted-foreground">
                @{host.username}
                <span aria-hidden> · </span>
                {placeLine}
              </p>
              <LegacyTierBadge
                tier={host.legacy_tier || host.legacy_status || "New Host"}
              />
              {host.display_score != null ? (
                <p className="text-xs font-semibold tabular-nums text-muted-foreground">
                  {host.legacy_tier || host.legacy_status || "Legacy"} ·{" "}
                  {host.display_score} Legacy Score
                  {host.is_provisional ? " · Provisional" : ""}
                </p>
              ) : null}
            </div>
          </div>

          <p className="line-clamp-1 text-sm leading-relaxed text-muted-foreground">
            {bio}
          </p>

          <StatsStrip
            upcoming={upcoming}
            ticketsSold={ticketsSold}
            rating={rating}
            upcomingHref={hostUpcomingHref}
          />

          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
            {nextEvent ? (
              eventHref ? (
                <Link
                  href={eventHref}
                  className="line-clamp-1 font-medium text-foreground/90 hover:text-primary hover:underline"
                >
                  Next: {nextEvent.title}
                </Link>
              ) : (
                <span className="line-clamp-1">Next: {nextEvent.title}</span>
              )
            ) : null}
            {host.sponsor_ready || host.vault_items_count > 0 ? (
              <CapabilityChips
                sponsorReady={host.sponsor_ready}
                vaultActive={host.vault_items_count > 0}
              />
            ) : null}
          </div>
        </div>

        {followError ? (
          <p className="text-xs text-danger">{followError}</p>
        ) : null}

        <footer className="mt-auto flex shrink-0 flex-col gap-2.5 pt-3">
          <Link
            href={href}
            className="w-full"
            onClick={() =>
              trackHostCardClick({
                hostId: host.host_id,
                username: host.username,
                target: "view_legacy",
              })
            }
          >
            <Button variant="dark" size="md" className="w-full padeya-btn-micro">
              View Legacy
            </Button>
          </Link>
          <div className="min-h-[2.25rem]">
            {ownHostLoading ? (
              <div
                className="h-9 w-full animate-pulse rounded-[var(--radius-sm)] bg-muted/35"
                aria-hidden
              />
            ) : isOwnHost ? (
              <p className="rounded-[var(--radius-sm)] border border-border/70 bg-muted/20 px-3 py-2 text-center text-xs leading-snug text-muted-foreground">
                This is your Legacy Page — you can&apos;t follow yourself. Fans
                use Follow on this card when they&apos;re signed in.
              </p>
            ) : (
              <HostFollowControls
                hostId={host.host_id}
                hostSlug={host.username}
                hostDisplayName={host.display_name}
                loginNextPath={href}
                initialFollowing={initiallyFollowing}
                size="md"
                layout="card-row"
                promptAfterFollow={false}
                onBeforeFollowToggle={() =>
                  trackHostFollowClick({
                    hostId: host.host_id,
                    username: host.username,
                  })
                }
                onError={setFollowError}
              />
            )}
          </div>
        </footer>
      </Card>
    </article>
  );
}
