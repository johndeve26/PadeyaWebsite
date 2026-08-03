"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";

import { ConnectButton } from "@/components/fan-connect/ConnectButton";
import { FanFollowButton } from "@/components/passport/FanFollowButton";
import { FanPassportSafetyMenu } from "@/components/passport/FanPassportSafetyMenu";
import { GenderBadge } from "@/components/profile/GenderBadge";
import { Badge, Button } from "@/components/ui";
import { enlargeableAttrs } from "@/components/media/ImageLightbox";
import { trackFanCardClick, trackFanCardImpression } from "@/lib/analytics";
import { cn } from "@/lib/cn";
import {
  directoryCardCtas,
  fanPageCtaMode,
  fanPageCtas,
} from "@/lib/own-fan-ctas";
import type { FanDirectoryCard } from "@/lib/types/passport";

function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "FP";
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

export function FanPassportCard({
  fan,
  listContext = "fans_directory",
  isOwnPassport = false,
}: {
  fan: FanDirectoryCard;
  listContext?: string;
  /** True when current_user.id === fan.user_id. */
  isOwnPassport?: boolean;
}) {
  const ref = useRef<HTMLElement | null>(null);
  const seen = useRef(false);
  const connections = fan.connections_count ?? 0;
  const pageCtas = fanPageCtas(fanPageCtaMode(isOwnPassport));
  const cardCtas = directoryCardCtas(isOwnPassport, fan.share_path);

  useEffect(() => {
    const el = ref.current;
    if (!el || seen.current) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          seen.current = true;
          trackFanCardImpression({
            username: fan.username,
            listContext,
          });
          io.disconnect();
        }
      },
      { threshold: 0.4 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [fan.username, listContext]);

  return (
    <article ref={ref} className="group h-full">
      <div
        className={cn(
          "relative flex h-full flex-col overflow-hidden rounded-[var(--radius-xl)]",
          "border border-ink/10 bg-card shadow-[var(--shadow)]",
          "transition-[transform,box-shadow,border-color] duration-300",
          "hover:-translate-y-0.5 hover:border-primary/45 hover:shadow-[var(--shadow-glow)]",
          "dark:border-paper/12 dark:bg-surface-elevated",
          isOwnPassport && "ring-1 ring-primary/35",
        )}
      >
        {/* Passport cover band */}
        <div className="relative overflow-hidden bg-ink px-5 pb-5 pt-4 text-paper sm:px-6">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-[0.16]"
            style={{
              backgroundImage:
                "repeating-linear-gradient(0deg, transparent, transparent 10px, color-mix(in srgb, var(--paper) 14%, transparent) 10px, color-mix(in srgb, var(--paper) 14%, transparent) 11px)",
            }}
          />
          <div
            aria-hidden
            className="pointer-events-none absolute -right-8 -top-10 h-28 w-28 rounded-full bg-primary/25 blur-2xl"
          />
          <div className="relative flex items-start gap-3.5">
            <div
              className={cn(
                "relative flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-full",
                "bg-surface-dark text-sm font-extrabold text-primary",
                "ring-2 ring-primary/55 shadow-[var(--shadow-glow)]",
              )}
              aria-hidden
            >
              {fan.avatar_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={fan.avatar_url}
                  alt={fan.display_name}
                  className="h-full w-full cursor-zoom-in object-cover"
                  {...enlargeableAttrs(fan.avatar_url, fan.display_name)}
                />
              ) : (
                initials(fan.display_name)
              )}
              <span className="absolute -bottom-0.5 -right-0.5 rounded-full border border-primary/40 bg-ink px-1 py-px text-[8px] font-extrabold uppercase tracking-wide text-primary">
                ✓
              </span>
            </div>
            <div className="min-w-0 flex-1 pt-0.5">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-[10px] font-extrabold uppercase tracking-[0.18em] text-primary">
                  Fan Passport
                </p>
                {isOwnPassport ? (
                  <Badge tone="accent" size="sm">
                    You
                  </Badge>
                ) : null}
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <h3 className="truncate text-lg font-extrabold tracking-tight text-paper">
                  {fan.display_name}
                </h3>
                {fan.gender_visible && fan.gender_short ? (
                  <GenderBadge
                    surface="onDark"
                    value={{
                      gender: fan.gender ?? null,
                      gender_short: fan.gender_short,
                      gender_label: fan.gender_label ?? null,
                      gender_visible: fan.gender_visible,
                    }}
                  />
                ) : null}
                {fan.is_superfan ? (
                  <Badge tone="accent" size="sm">
                    Superfan
                  </Badge>
                ) : null}
              </div>
              <p className="text-sm font-semibold text-paper/60">
                @{fan.username}
              </p>
            </div>
          </div>
        </div>

        <div className="relative flex flex-1 flex-col gap-4 p-5 sm:p-6">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-3 rounded-[calc(var(--radius-xl)-6px)] border border-dashed border-primary/20"
          />

          <p className="relative line-clamp-2 text-sm leading-relaxed text-body">
            {fan.tagline?.trim() || "Verified nightlife history on Pàdéyá."}
          </p>

          <div className="relative flex flex-wrap gap-1.5">
            {fan.city_label ? (
              <Badge tone="outline" size="sm">
                {fan.city_label}
              </Badge>
            ) : null}
            {fan.favorite_scene ? (
              <Badge tone="neutral" size="sm">
                {fan.favorite_scene}
              </Badge>
            ) : null}
            {fan.top_badges.length ? (
              fan.top_badges.map((b) => (
                <Badge key={b.slug} tone="accent" size="sm">
                  {b.name}
                </Badge>
              ))
            ) : (
              <Badge tone="outline" size="sm">
                Badges coming soon
              </Badge>
            )}
          </div>

          <dl className="relative grid grid-cols-3 gap-2 rounded-[var(--radius-lg)] border border-border/80 bg-surface-muted/70 px-3 py-3 dark:bg-surface-inset/60">
            <div>
              <dt className="text-xs font-semibold text-muted-foreground">
                Events attended
              </dt>
              <dd className="mt-0.5 text-xl font-extrabold tabular-nums tracking-tight text-heading">
                {fan.stats_limited && !fan.events_attended
                  ? "—"
                  : fan.events_attended}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-muted-foreground">
                Hosts followed
              </dt>
              <dd className="mt-0.5 text-xl font-extrabold tabular-nums tracking-tight text-heading">
                {fan.hosts_followed}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold text-muted-foreground">
                Connections
              </dt>
              <dd className="mt-0.5 text-xl font-extrabold tabular-nums tracking-tight text-heading">
                {connections}
              </dd>
            </div>
          </dl>

          <p className="relative text-xs font-semibold text-muted-foreground">
            {fan.latest_badge_name
              ? `Latest stamp: ${fan.latest_badge_name}`
              : fan.stats_limited
                ? "Public stats limited"
                : "Verified on Pàdéyá"}
          </p>

          <div className="relative mt-auto space-y-2.5 pt-1">
            {isOwnPassport ? (
              <>
                {cardCtas.edit ? (
                  <Link href={cardCtas.edit.href}>
                    <Button className="w-full" size="md" variant="secondary">
                      {cardCtas.edit.label}
                    </Button>
                  </Link>
                ) : null}
                {cardCtas.view ? (
                  <Link
                    href={cardCtas.view.href}
                    className="block"
                    onClick={() =>
                      trackFanCardClick({
                        username: fan.username,
                        listContext,
                      })
                    }
                  >
                    <Button className="w-full" size="md">
                      {cardCtas.view.label}
                    </Button>
                  </Link>
                ) : null}
              </>
            ) : (
              <>
                <FanFollowButton
                  isOwnPassport={false}
                  showFollow={pageCtas.showFollow}
                  ctas={pageCtas}
                  targetUserId={fan.user_id}
                />
                <ConnectButton
                  username={fan.username}
                  passportOwnerUserId={fan.user_id}
                  showConnect={
                    pageCtas.showConnect && pageCtas.showConnectionRequest
                  }
                  showMessage={
                    pageCtas.showMessage && pageCtas.showFanToFanMessage
                  }
                  size="md"
                  compact
                  surface="light"
                />
                <FanPassportSafetyMenu
                  username={fan.username}
                  passportOwnerUserId={fan.user_id}
                  isOwnPassport={false}
                  ctas={pageCtas}
                  compact
                />
                <Link
                  href={fan.share_path}
                  className="block"
                  onClick={() =>
                    trackFanCardClick({
                      username: fan.username,
                      listContext,
                    })
                  }
                >
                  <Button className="w-full" size="md">
                    View Passport
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
