"use client";

import Link from "next/link";

import { ConnectButton } from "@/components/fan-connect/ConnectButton";
import { headerDarkSurfaceProps } from "@/components/layout/headerSurface";
import { FanFollowButton } from "@/components/passport/FanFollowButton";
import { FanPassportSafetyMenu } from "@/components/passport/FanPassportSafetyMenu";
import { Badge, Button, Container, Media } from "@/components/ui";
import { fanPageCtas } from "@/lib/own-fan-ctas";
import { fanAvatarAlt } from "@/lib/seo/image-alt";
import type { FanPassportPublicPage } from "@/lib/types/passport";

type FanCtas = ReturnType<typeof fanPageCtas>;

type Props = {
  page: FanPassportPublicPage;
  isOwnPassport?: boolean;
  /** False while auth resolves so Connect does not flash for the owner. */
  ownershipReady?: boolean;
  ctas?: FanCtas;
};

export function FanPassportHero({
  page,
  isOwnPassport = false,
  ownershipReady = true,
  ctas,
}: Props) {
  const resolved =
    ctas ?? fanPageCtas(isOwnPassport ? "own_passport" : "visitor");
  const mark = page.display_name.trim().slice(0, 1).toUpperCase() || "F";
  const scene = page.favorite_categories[0] ?? null;
  const city = page.favorite_cities[0] ?? null;
  const showVisitorActions =
    ownershipReady &&
    !isOwnPassport &&
    (page.visibility === "public" || page.visibility === "unlisted");

  return (
    <section
      {...headerDarkSurfaceProps}
      className="relative overflow-hidden bg-ink text-paper"
    >
      <div
        aria-hidden
        className="padeya-hero-glow pointer-events-none absolute inset-0"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.14]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 11px, color-mix(in srgb, var(--paper) 12%, transparent) 11px, color-mix(in srgb, var(--paper) 12%, transparent) 12px)",
        }}
      />
      <Container className="relative max-w-[1180px] py-12 sm:py-14">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-end">
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="accent">Fan Passport</Badge>
            </div>
            <div className="flex items-start gap-4 sm:gap-5">
              <div className="relative shrink-0">
                <div className="relative flex h-[4.5rem] w-[4.5rem] items-center justify-center overflow-hidden rounded-full border-2 border-primary/60 bg-surface-dark text-2xl font-extrabold text-primary shadow-[var(--shadow-glow)] sm:h-24 sm:w-24 sm:text-3xl">
                  {page.avatar_url ? (
                    <Media
                      src={page.avatar_url}
                      alt={fanAvatarAlt(page.display_name)}
                      className="h-full w-full object-cover"
                      sizes="avatarMd"
                      loading="eager"
                    />
                  ) : (
                    mark
                  )}
                </div>
                <span
                  className="absolute -bottom-1 -right-1 rounded-full border border-primary/40 bg-ink px-1.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wide text-primary"
                  title="Verified check-in history"
                >
                  Verified
                </span>
              </div>
              <div className="min-w-0 space-y-2">
                <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-[2.75rem]">
                  {page.display_name}
                </h1>
                <p className="text-sm font-semibold text-paper/65">
                  @{page.username}
                </p>
                <p className="max-w-xl text-base leading-relaxed text-paper/75">
                  {page.tagline?.trim() ||
                    "Verified event history, badges, reviews, and host support on Pàdéyá."}
                </p>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  <Badge
                    tone="outline"
                    size="sm"
                    className="border-paper/30 text-paper/85"
                  >
                    {page.visibility === "unlisted"
                      ? "Unlisted Passport"
                      : "Public Passport"}
                  </Badge>
                  {page.is_superfan ? (
                    <Badge tone="accent" size="sm">
                      Superfan
                    </Badge>
                  ) : null}
                  {city ? (
                    <Badge
                      tone="outline"
                      size="sm"
                      className="border-paper/25 text-paper/75"
                    >
                      {city}
                    </Badge>
                  ) : null}
                  {scene ? (
                    <Badge
                      tone="outline"
                      size="sm"
                      className="border-paper/25 text-paper/75"
                    >
                      {scene}
                    </Badge>
                  ) : null}
                </div>
              </div>
            </div>
            {page.bio ? (
              <p className="max-w-2xl text-sm leading-relaxed text-paper/70 sm:text-base">
                {page.bio}
              </p>
            ) : null}
            {isOwnPassport ? (
              <div className="space-y-2">
                <h2 className="text-xl font-extrabold tracking-tight text-paper sm:text-2xl">
                  {resolved.title ?? "This is your Fan Passport"}
                </h2>
                {resolved.description ? (
                  <p className="max-w-xl text-sm leading-relaxed text-paper/70 sm:text-base">
                    {resolved.description}
                  </p>
                ) : null}
              </div>
            ) : null}
            <div className="flex flex-wrap items-center gap-3">
              {isOwnPassport ? (
                <>
                  {resolved.primary ? (
                    <Link href={resolved.primary.href}>
                      <Button size="lg" variant="secondary">
                        {resolved.primary.label}
                      </Button>
                    </Link>
                  ) : null}
                  {resolved.secondary ? (
                    <Link href={resolved.secondary.href}>
                      <Button size="lg" variant="outline-dark">
                        {resolved.secondary.label}
                      </Button>
                    </Link>
                  ) : null}
                  {resolved.allowShare &&
                  resolved.share &&
                  page.share_path ? (
                    <Link href={page.share_path} target="_blank" rel="noreferrer">
                      <Button size="lg" variant="outline-dark">
                        {resolved.share.label}
                      </Button>
                    </Link>
                  ) : null}
                </>
              ) : showVisitorActions ? (
                <>
                  <FanFollowButton
                    isOwnPassport={false}
                    showFollow={resolved.showFollow}
                    ctas={resolved}
                    targetUserId={page.user_id}
                  />
                  <ConnectButton
                    username={page.username}
                    passportOwnerUserId={page.user_id}
                    showConnect={
                      resolved.showConnect &&
                      resolved.showConnectionRequest &&
                      page.visibility === "public"
                    }
                    showMessage={
                      resolved.showMessage && resolved.showFanToFanMessage
                    }
                  />
                  <FanPassportSafetyMenu
                    username={page.username}
                    passportOwnerUserId={page.user_id}
                    isOwnPassport={false}
                    ctas={resolved}
                  />
                </>
              ) : null}
              <p
                className="inline-flex items-baseline gap-1.5 text-base font-extrabold tracking-tight text-paper sm:text-lg"
                aria-label={`${page.connections_count ?? 0} connections`}
              >
                <span className="tabular-nums text-primary">
                  {page.connections_count ?? 0}
                </span>
                <span className="text-sm font-bold text-paper/80 sm:text-base">
                  {(page.connections_count ?? 0) === 1
                    ? "connection"
                    : "connections"}
                </span>
              </p>
            </div>
          </div>

          <aside className="relative hidden overflow-hidden rounded-[var(--radius-xl)] border border-paper/15 bg-paper/5 p-5 backdrop-blur-sm lg:block">
            <div
              aria-hidden
              className="pointer-events-none absolute inset-3 rounded-[calc(var(--radius-xl)-4px)] border border-dashed border-primary/35"
            />
            <p className="relative text-[11px] font-extrabold uppercase tracking-[0.18em] text-primary">
              Passport seal
            </p>
            <p className="relative mt-3 text-lg font-extrabold tracking-tight">
              Verified on Pàdéyá
            </p>
            <p className="relative mt-2 text-sm leading-relaxed text-paper/65">
              {page.events_attended === 1
                ? "1 check-in"
                : `${page.events_attended} check-ins`}{" "}
              ·{" "}
              {page.badges_earned_count === 1
                ? "1 stamp"
                : `${page.badges_earned_count} stamps`}{" "}
              ·{" "}
              {page.hosts_followed === 1
                ? "1 host"
                : `${page.hosts_followed} hosts`}
            </p>
            <p className="relative mt-4 text-xs text-paper/50">
              Private tickets, spend, and hidden venues never appear here.
            </p>
          </aside>
        </div>
      </Container>
    </section>
  );
}
