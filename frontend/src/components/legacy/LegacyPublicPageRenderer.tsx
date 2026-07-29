"use client";

import Link from "next/link";
import { useMemo, useState, type ReactNode } from "react";

import { HostFollowControls } from "@/components/hosts/HostFollowControls";
import { StartMessageButton } from "@/components/messaging/StartMessageButton";
import { LegacyEventCard } from "@/components/legacy/LegacyEventCard";
import { LegacySocialIcon } from "@/components/legacy/LegacySocialIcon";
import { GenderBadge } from "@/components/profile/GenderBadge";
import {
  Badge,
  Button,
  Card,
  Container,
  EmptyState,
  LegacyTierBadge,
  Media,
  MemoryCard,
  ReviewCard,
  SectionHeader,
} from "@/components/ui";
import { useHostAffiliation } from "@/hooks/useHostAffiliation";
import { cn } from "@/lib/cn";
import { sponsorshipMarketplaceUrl } from "@/lib/sponsor-marketplace-paths";
import { hostPageCtaMode, hostPageCtas } from "@/lib/own-host-ctas";
import { hostAvatarAlt, hostCoverAlt } from "@/lib/seo/image-alt";
import {
  formatCompact,
  formatLegacyDate,
  resolveHostMedia,
  socialPlatformLabel,
} from "@/lib/legacy-presentation";
import type {
  LegacyContentBlock,
  LegacyPage,
  LegacyVaultPreviewCard,
} from "@/lib/types/legacy";
import { VAULT_EXAMPLES, VAULT_LEGACY_BLOCK_DESCRIPTION } from "@/lib/vault-copy";

function LockedVaultPreviewCard({
  item,
  username,
  compact = false,
  spotlight = false,
}: {
  item: LegacyVaultPreviewCard;
  username: string;
  compact?: boolean;
  spotlight?: boolean;
}) {
  const href = item.share_path || `/u/${username}/vault/${item.slug}`;
  const typeLabel = item.content_type || item.access_type || null;
  const priceLabel =
    item.price != null && item.currency
      ? `${item.currency} ${Number(item.price).toLocaleString()}`
      : item.price != null
        ? String(item.price)
        : null;

  return (
    <Link
      href={href}
      className={
        spotlight
          ? "group padeya-legacy-glass grid overflow-hidden rounded-[var(--radius-lg)] transition-transform duration-200 hover:-translate-y-0.5 sm:grid-cols-[1.2fr_1fr]"
          : compact
            ? "group padeya-legacy-glass flex min-w-[240px] max-w-[280px] shrink-0 gap-3 overflow-hidden rounded-[var(--radius-lg)] p-3 transition-transform duration-200 hover:-translate-y-0.5"
            : "group padeya-legacy-glass block overflow-hidden rounded-[var(--radius-lg)] transition-transform duration-200 hover:-translate-y-1"
      }
    >
      <div
        className={
          spotlight
            ? "relative aspect-[16/10] bg-ink sm:aspect-auto sm:min-h-[240px]"
            : compact
              ? "relative h-[4.5rem] w-[4.5rem] shrink-0 overflow-hidden rounded-[var(--radius-md)] bg-ink"
              : "relative aspect-[16/10] bg-ink"
        }
      >
        {item.cover_url ? (
          <Media
            src={item.cover_url}
            alt={item.title || "Vault item"}
            className="h-full w-full object-cover opacity-90 transition-transform duration-500 group-hover:scale-[1.05]"
          />
        ) : (
          <div className="padeya-hero-glow absolute inset-0" />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-ink/70 via-transparent to-transparent" />
        <div className="absolute left-2 top-2 flex flex-wrap gap-1">
          <Badge tone="accent">Locked</Badge>
          <Badge tone="dark">Exclusive</Badge>
          {item.featured ? (
            <Badge tone="outline" className="border-paper/30 text-paper">
              Featured
            </Badge>
          ) : null}
        </div>
      </div>
      <div className={compact ? "min-w-0 space-y-1 py-0.5" : "space-y-2 p-4 sm:p-5"}>
        {typeLabel ? (
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-subtle-foreground">
            {typeLabel.replace(/_/g, " ")}
          </p>
        ) : null}
        <h3
          className={
            spotlight
              ? "text-xl font-extrabold text-paper sm:text-2xl"
              : "text-base font-extrabold text-paper sm:text-lg"
          }
        >
          {item.title}
        </h3>
        {item.preview_text ? (
          <p
            className={
              compact
                ? "line-clamp-2 text-xs text-subtle-foreground"
                : "line-clamp-2 text-sm leading-relaxed text-subtle-foreground"
            }
          >
            {item.preview_text}
          </p>
        ) : null}
        {priceLabel ? (
          <p className="text-sm font-bold text-accent">{priceLabel}</p>
        ) : null}
      </div>
    </Link>
  );
}

function SidebarSection({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-3 px-5 py-5 sm:px-6 sm:py-5">
      <div>
        <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
          {eyebrow}
        </p>
        {title ? (
          <h3 className="mt-1 text-lg font-extrabold tracking-tight text-foreground">
            {title}
          </h3>
        ) : null}
      </div>
      {children}
    </div>
  );
}

function ReputationStat({
  label,
  value,
  hint,
  highlight = false,
}: {
  label: string;
  value: string;
  hint?: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-md)] px-3 py-3",
        highlight
          ? "border border-primary/35 bg-[color-mix(in_srgb,var(--primary)_10%,transparent)]"
          : "border border-border bg-surface-inset",
      )}
    >
      <p className="text-2xl font-extrabold tracking-tight text-heading sm:text-[1.75rem]">
        {value}
      </p>
      <p className="mt-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </p>
      {hint ? <p className="mt-1 text-[11px] text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

function HeroStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-[7rem] flex-1 rounded-[var(--radius-md)] border border-paper/10 bg-paper/[0.04] px-3 py-3 text-center backdrop-blur-sm sm:min-w-[8rem] sm:px-4 sm:py-3.5">
      <p className="text-xl font-extrabold tracking-tight text-paper sm:text-2xl">
        {value}
      </p>
      <p className="mt-1 text-[10px] font-bold uppercase tracking-[0.14em] text-paper/65">
        {label}
      </p>
    </div>
  );
}

function DiscoveryChip({
  href,
  label,
  icon,
}: {
  href: string;
  label: string;
  icon: ReactNode;
}) {
  return (
    <Link
      href={href}
      className="group inline-flex items-center gap-2.5 rounded-[var(--radius-md)] border border-border bg-card px-4 py-3 text-sm font-bold text-foreground shadow-[var(--shadow-soft)] transition-[transform,border-color,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-border-strong/25 hover:shadow-[var(--shadow)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background dark:bg-surface-elevated"
    >
      <span
        className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-sm)] bg-ink text-accent transition-transform duration-200 group-hover:scale-105"
        aria-hidden
      >
        {icon}
      </span>
      {label}
    </Link>
  );
}

function defaultBlocks(): LegacyContentBlock[] {
  return [
    { id: "d1", host_id: "", block_type: "about", title_override: "About", description_override: null, is_visible: true, sort_order: 0, layout_style: "prose", source_type: "automatic", item_limit: null, config: null },
    { id: "d2", host_id: "", block_type: "upcoming_events", title_override: "Upcoming events", description_override: null, is_visible: true, sort_order: 1, layout_style: "premium_cards", source_type: "automatic", item_limit: 3, config: null },
    { id: "d3", host_id: "", block_type: "past_events", title_override: "Past events", description_override: null, is_visible: true, sort_order: 2, layout_style: "premium_cards", source_type: "automatic", item_limit: 6, config: null },
    { id: "d4", host_id: "", block_type: "event_memories", title_override: "Event Memories", description_override: null, is_visible: true, sort_order: 3, layout_style: "memory_cards", source_type: "automatic", item_limit: 6, config: null },
    { id: "d5", host_id: "", block_type: "verified_reviews", title_override: "Verified reviews", description_override: null, is_visible: true, sort_order: 4, layout_style: "verified_quotes", source_type: "automatic", item_limit: 5, config: null },
    { id: "d6", host_id: "", block_type: "vault_preview", title_override: "Vault", description_override: null, is_visible: true, sort_order: 5, layout_style: "locked_cards", source_type: "automatic", item_limit: 3, config: null },
    { id: "d7", host_id: "", block_type: "sponsor_packages", title_override: "Sponsorship", description_override: null, is_visible: true, sort_order: 6, layout_style: "cta_panel", source_type: "automatic", item_limit: 3, config: null },
    { id: "d8", host_id: "", block_type: "related_discovery", title_override: "Keep exploring", description_override: null, is_visible: true, sort_order: 7, layout_style: "discovery_row", source_type: "automatic", item_limit: 6, config: null },
    { id: "d9", host_id: "", block_type: "contact_cta", title_override: "Get in touch", description_override: null, is_visible: true, sort_order: 8, layout_style: "cta_panel", source_type: "automatic", item_limit: null, config: null },
  ];
}

function resolveCtaHref(
  type: string | null | undefined,
  value: string | null | undefined,
  username: string,
): string | null {
  if (!value && type === "vault") return `/u/${username}/vault`;
  if (!value && type === "events") return "#upcoming-events";
  if (!value && type === "sponsors") return sponsorshipMarketplaceUrl(username);
  if (!value) return null;
  if (value.startsWith("http") || value.startsWith("/") || value.startsWith("#")) {
    return value;
  }
  if (type === "email") return `mailto:${value}`;
  return value;
}

function CtaLink({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  if (href.startsWith("http") || href.startsWith("mailto:")) {
    return (
      <a href={href} className="inline-flex">
        {children}
      </a>
    );
  }
  if (href.startsWith("#")) {
    return (
      <a href={href} className="inline-flex">
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className="inline-flex">
      {children}
    </Link>
  );
}

export function LegacyPublicPageRenderer({ page }: { page: LegacyPage }) {
  const [shareNote, setShareNote] = useState<string | null>(null);
  const [followDelta, setFollowDelta] = useState(0);
  const { affiliated: isOwnHost } = useHostAffiliation({
    hostId: page.host_id,
    hostSlug: page.username,
  });
  const hostCtas = hostPageCtas(hostPageCtaMode(isOwnHost));

  const media = resolveHostMedia(
    page.username,
    page.profile?.cover_url,
    page.profile?.avatar_url,
  );
  const avg =
    page.stats.average_verified_rating != null
      ? Number(page.stats.average_verified_rating).toFixed(1)
      : "—";
  const followerCount = Math.max(0, page.stats.followers + followDelta);
  const tierLabel = page.tier?.slug || page.tier?.name || page.legacy_status;
  const location = [page.profile?.city, page.profile?.state, page.profile?.country]
    .filter(Boolean)
    .join(", ");
  const tagline = page.tagline || page.settings?.tagline || null;
  const bio =
    page.about ||
    page.profile?.bio ||
    "Verified Pàdéyá host building nights, reputation, and fan loyalty.";
  const blocks = useMemo(() => {
    const rows = (page.content_blocks?.length ? page.content_blocks : defaultBlocks())
      .filter((b) => b.is_visible)
      .slice()
      .sort((a, b) => a.sort_order - b.sort_order);
    return rows;
  }, [page.content_blocks]);

  const vaultItems = page.vault_preview ?? [];
  const sponsorPackages = page.sponsor_packages ?? [];
  const settings = page.settings;
  const primaryHref = resolveCtaHref(
    settings?.primary_cta_type,
    settings?.primary_cta_value,
    page.username,
  );
  const secondaryHref = resolveCtaHref(
    settings?.secondary_cta_type,
    settings?.secondary_cta_value,
    page.username,
  );
  const contactHref =
    page.contact?.public_email
      ? `mailto:${page.contact.public_email}`
      : page.contact?.preference && page.contact.preference !== "none"
        ? "#contact"
        : null;
  const bookHref =
    settings?.sponsorship_available || sponsorPackages.length > 0
      ? "#sponsorship"
      : primaryHref?.includes("sponsor")
        ? primaryHref
        : null;

  const serviceAreas = Array.isArray(settings?.service_areas)
    ? settings.service_areas
        .map((area) => (typeof area === "string" ? area : null))
        .filter((area): area is string => Boolean(area))
    : [];

  const shareUrl = useMemo(() => {
    if (typeof window === "undefined") return page.share_path;
    return `${window.location.origin}${page.share_path}`;
  }, [page.share_path]);

  async function onShare() {
    try {
      if (navigator.share) {
        await navigator.share({
          title: `${page.display_name} on Pàdéyá`,
          url: shareUrl,
        });
        return;
      }
      await navigator.clipboard.writeText(shareUrl);
      setShareNote("Link copied");
    } catch {
      setShareNote("Unable to share");
    }
  }

  function renderBlock(block: LegacyContentBlock) {
    const title = block.title_override || block.block_type;
    const description = block.description_override || undefined;

    switch (block.block_type) {
      case "about":
        return (
          <section key={block.id} className="padeya-fade-up space-y-4">
            <SectionHeader
              eyebrow="Profile"
              title={title}
              description={description || "Who this host is and what they bring to the night."}
            />
            <p className="max-w-3xl whitespace-pre-wrap text-base leading-[1.75] text-body sm:text-lg sm:leading-[1.75]">
              {page.about || page.profile?.bio || "This host has not added a full bio yet."}
            </p>
            {(page.social_links?.length ?? 0) > 0 ? (
              <ul className="flex flex-wrap gap-2.5" aria-label="Social links">
                {page.social_links!.map((link) => (
                  <li key={`${link.platform}-${link.url}`}>
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 rounded-[var(--radius-md)] border border-border bg-muted/80 px-3.5 py-2 text-sm font-bold text-foreground transition-[transform,border-color] duration-200 hover:-translate-y-0.5 hover:border-border-strong/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background"
                    >
                      <LegacySocialIcon platform={link.platform} />
                      {link.label || socialPlatformLabel(link.platform)}
                    </a>
                  </li>
                ))}
              </ul>
            ) : page.profile?.website ? (
              <a
                href={page.profile.website}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 text-base font-bold text-foreground underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background"
              >
                <LegacySocialIcon platform="website" />
                {page.profile.website.replace(/^https?:\/\//, "")}
              </a>
            ) : null}
          </section>
        );

      case "upcoming_events":
        return (
          <section key={block.id} id="upcoming-events" className="padeya-fade-up space-y-4">
            <SectionHeader
              eyebrow="Calendar"
              title={title}
              description={description || "Nights on the calendar — tickets and details live here."}
            />
            {page.upcoming_events.length === 0 ? (
              <EmptyState
                title="No upcoming events"
                description="Check back soon — this host has not published the next show yet."
              />
            ) : (
              <div className="grid gap-5 sm:grid-cols-2 xl:gap-6">
                {page.upcoming_events.map((event) => (
                  <LegacyEventCard key={event.id} event={event} variant="upcoming" />
                ))}
              </div>
            )}
          </section>
        );

      case "past_events":
        return (
          <section key={block.id} className="padeya-fade-up space-y-4">
            <SectionHeader
              eyebrow="Archive"
              title={title}
              description={description || "Completed nights and the reputation behind them."}
            />
            {page.past_events.length === 0 ? (
              <EmptyState title="No past events yet" />
            ) : (
              <div className="grid gap-5 sm:grid-cols-2 xl:gap-6">
                {page.past_events.map((event) => (
                  <LegacyEventCard key={event.id} event={event} variant="past" />
                ))}
              </div>
            )}
          </section>
        );

      case "event_memories":
        if ((page.event_memories?.length ?? 0) === 0) return null;
        return (
          <section key={block.id} id="memories" className="padeya-fade-up space-y-4">
            <SectionHeader
              eyebrow="Recaps"
              title={title}
              description={description || "Media-first stories from nights that already happened."}
            />
            <div className="grid gap-5 sm:grid-cols-2 xl:gap-6">
              {(page.event_memories ?? []).map((memory) => (
                <MemoryCard
                  key={memory.id}
                  title={memory.event_title}
                  href={memory.share_path}
                  dateLabel={formatLegacyDate(memory.start_datetime)}
                  city={memory.city}
                  imageUrl={memory.banner_url}
                  rating={
                    memory.verified_rating != null
                      ? Number(memory.verified_rating)
                      : null
                  }
                />
              ))}
            </div>
          </section>
        );

      case "verified_reviews":
        return (
          <section key={block.id} className="padeya-fade-up space-y-4">
            <div className="space-y-3">
              <SectionHeader
                eyebrow="Trust"
                title={title}
                description={
                  description ||
                  `${page.stats.review_count} review${page.stats.review_count === 1 ? "" : "s"} from real nights out.`
                }
              />
              <p className="rounded-[var(--radius-md)] border border-accent/30 bg-[color-mix(in_srgb,var(--primary)_8%,transparent)] px-4 py-3 text-sm font-medium leading-relaxed text-foreground sm:text-base">
                {isOwnHost
                  ? "You can’t publicly review your own host workspace."
                  : "Only attendees checked in with a valid Pàdéyá QR ticket can review this host."}
              </p>
            </div>
            {page.reviews.length === 0 ? (
              <EmptyState
                title="No verified reviews yet"
                description="Ratings appear after attendees check in and the event completes."
              />
            ) : (
              <div className="space-y-3.5">
                {page.reviews.map((review) => (
                  <ReviewCard
                    key={review.id}
                    rating={review.rating}
                    title={review.title}
                    body={review.body}
                    reviewerName={review.reviewer_name}
                    eventTitle={review.event_title}
                    eventHref={
                      review.event_slug
                        ? `/events/${review.event_slug}`
                        : null
                    }
                    reply={review.reply}
                    dateLabel={formatLegacyDate(review.created_at)}
                  />
                ))}
              </div>
            )}
          </section>
        );

      case "vault_preview": {
        const layout = block.layout_style || "locked_cards";
        const featuredItem =
          vaultItems.find((item) => item.featured) ?? vaultItems[0] ?? null;
        const restItems =
          layout === "featured_spotlight" && featuredItem
            ? vaultItems.filter((item) => item.id !== featuredItem.id)
            : vaultItems;

        return (
          <section
            key={block.id}
            id="vault"
            className="padeya-fade-up overflow-hidden rounded-[var(--radius-xl)] bg-ink text-paper"
          >
            <div className="relative px-5 py-7 sm:px-8 sm:py-9">
              <div
                aria-hidden
                className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-70"
              />
              <div
                aria-hidden
                className="padeya-legacy-radar pointer-events-none absolute inset-0 opacity-40"
              />
              <div className="relative space-y-5">
                <div className="flex flex-wrap items-end justify-between gap-4">
                  <div className="max-w-xl space-y-2">
                    <SectionHeader
                      tone="dark"
                      eyebrow="Vault"
                      title={title}
                      description={description || VAULT_LEGACY_BLOCK_DESCRIPTION}
                    />
                  </div>
                  <Link href={`/u/${page.username}/vault`} className="padeya-btn-micro">
                    <Button size="lg">Open Vault</Button>
                  </Link>
                </div>
                {vaultItems.length > 0 ? (
                  layout === "featured_spotlight" && featuredItem ? (
                    <div className="space-y-4">
                      <LockedVaultPreviewCard
                        item={featuredItem}
                        username={page.username}
                        spotlight
                      />
                      {restItems.length > 0 ? (
                        <div className="grid gap-4 sm:grid-cols-2">
                          {restItems.map((item) => (
                            <LockedVaultPreviewCard
                              key={item.id}
                              item={item}
                              username={page.username}
                            />
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ) : layout === "compact_row" ? (
                    <div className="flex gap-3 overflow-x-auto pb-1">
                      {vaultItems.map((item) => (
                        <LockedVaultPreviewCard
                          key={item.id}
                          item={item}
                          username={page.username}
                          compact
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="grid gap-4 sm:grid-cols-2">
                      {vaultItems.map((item) => (
                        <LockedVaultPreviewCard
                          key={item.id}
                          item={item}
                          username={page.username}
                        />
                      ))}
                    </div>
                  )
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {VAULT_EXAMPLES.slice(0, 4).map((line) => (
                      <div
                        key={line}
                        className="padeya-legacy-glass space-y-3 rounded-[var(--radius-lg)] p-4"
                      >
                        <Badge tone="accent">Locked</Badge>
                        <p className="text-sm font-semibold leading-relaxed text-subtle-foreground">
                          {line}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </section>
        );
      }

      case "sponsor_packages":
        return (
          <section key={block.id} id="sponsorship" className="padeya-fade-up space-y-4">
            <SectionHeader
              eyebrow="Brands"
              title={title}
              description={description || "Packages built for brands that want proven nightlife reach."}
            />
            {sponsorPackages.length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2 xl:gap-5">
                {sponsorPackages.map((slot) => (
                  <Card
                    key={slot.id}
                    className="relative flex h-full flex-col space-y-4 overflow-hidden border-border pt-6 shadow-[var(--shadow-soft)] transition-[transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:shadow-[var(--shadow)]"
                  >
                    <div
                      aria-hidden
                      className="absolute inset-x-0 top-0 h-1 bg-accent"
                    />
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone="accent">{slot.slot_type.replace(/_/g, " ")}</Badge>
                      {slot.accepting_sponsors ? (
                        <Badge tone="neutral">Open</Badge>
                      ) : null}
                    </div>
                    <div className="space-y-1">
                      <p className="text-3xl font-extrabold tracking-tight text-foreground">
                        {slot.currency} {Number(slot.price).toLocaleString()}
                      </p>
                      <h3 className="text-lg font-extrabold text-foreground">
                        {slot.title}
                      </h3>
                    </div>
                    <p className="flex-1 text-sm leading-relaxed text-muted-foreground sm:text-base">
                      {slot.description}
                    </p>
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                      Est. reach · {formatCompact(page.stats.tickets_sold)} tickets sold
                      {page.stats.followers
                        ? ` · ${formatCompact(followerCount)} followers`
                        : ""}
                    </p>
                    <Link href={sponsorshipMarketplaceUrl(page.username)}>
                      <Button size="lg" variant="secondary" className="w-full padeya-btn-micro">
                        Book Package
                      </Button>
                    </Link>
                  </Card>
                ))}
              </div>
            ) : (
              <Card className="space-y-4 border-accent/25 bg-[linear-gradient(145deg,color-mix(in_srgb,var(--primary)_8%,transparent),transparent_50%)]">
                <h3 className="text-xl font-extrabold text-foreground">
                  Sponsor this host
                </h3>
                <p className="text-base leading-relaxed text-muted-foreground">
                  {settings?.sponsorship_note ||
                    "Browse verified creators and open sponsorship packages on Pàdéyá."}
                </p>
                <Link href={sponsorshipMarketplaceUrl(page.username)}>
                  <Button size="lg" variant="secondary" className="padeya-btn-micro">
                    Explore sponsorships
                  </Button>
                </Link>
              </Card>
            )}
          </section>
        );

      case "contact_cta":
        if ((page.contact?.preference || "none") === "none" && !page.contact?.note) {
          return null;
        }
        return (
          <section key={block.id} id="contact" className="padeya-fade-up space-y-4">
            <SectionHeader
              eyebrow="Contact"
              title={title}
              description={description || "Reach out for bookings, collabs, and press."}
            />
            <Card className="space-y-3">
              {page.contact?.note ? (
                <p className="text-base leading-relaxed text-muted-foreground">
                  {page.contact.note}
                </p>
              ) : null}
              {page.contact?.public_email ? (
                <a
                  href={`mailto:${page.contact.public_email}`}
                  className="text-base font-bold text-foreground underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background"
                >
                  {page.contact.public_email}
                </a>
              ) : null}
              {page.contact?.preferred_channel ? (
                <p className="text-sm text-muted-foreground">
                  Preferred: {page.contact.preferred_channel}
                </p>
              ) : null}
            </Card>
          </section>
        );

      case "related_discovery":
        return (
          <section key={block.id} className="padeya-fade-up space-y-4">
            <SectionHeader
              eyebrow="Discover"
              title={title}
              description={description || "Keep exploring events, hosts, cities, and Vault drops."}
            />
            <div className="flex flex-wrap gap-3">
              <DiscoveryChip
                href="/events"
                label="Events"
                icon={
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                    <rect x="3" y="5" width="18" height="16" rx="2" />
                    <path d="M3 10h18M8 3v4M16 3v4" />
                  </svg>
                }
              />
              <DiscoveryChip
                href="/hosts"
                label="Hosts"
                icon={
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                    <circle cx="12" cy="8" r="3.5" />
                    <path d="M5 19c1.5-3 4-4.5 7-4.5S17.5 16 19 19" />
                  </svg>
                }
              />
              {page.profile?.city ? (
                <DiscoveryChip
                  href={`/events/city/${encodeURIComponent(
                    page.profile.city.toLowerCase().replace(/\s+/g, "-"),
                  )}`}
                  label={page.profile.city}
                  icon={
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                      <path d="M12 21s7-5.2 7-11a7 7 0 1 0-14 0c0 5.8 7 11 7 11Z" />
                      <circle cx="12" cy="10" r="2.2" />
                    </svg>
                  }
                />
              ) : (
                <DiscoveryChip
                  href="/events/location"
                  label="Cities"
                  icon={
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                      <path d="M12 21s7-5.2 7-11a7 7 0 1 0-14 0c0 5.8 7 11 7 11Z" />
                      <circle cx="12" cy="10" r="2.2" />
                    </svg>
                  }
                />
              )}
              <DiscoveryChip
                href={
                  settings?.primary_category_slug
                    ? `/events/c/${encodeURIComponent(settings.primary_category_slug)}`
                    : "/events"
                }
                label="Genres"
                icon={
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                    <path d="M9 18V6l10-2v12" />
                    <circle cx="7" cy="18" r="2" />
                    <circle cx="17" cy="16" r="2" />
                  </svg>
                }
              />
              <DiscoveryChip
                href={`/@${page.username}/vault`}
                label="Vault"
                icon={
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                    <rect x="4" y="10" width="16" height="10" rx="2" />
                    <path d="M8 10V7a4 4 0 0 1 8 0v3" />
                  </svg>
                }
              />
              {(page.event_memories?.length ?? 0) > 0 ? (
                <DiscoveryChip
                  href="#memories"
                  label="Memories"
                  icon={
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                      <rect x="3" y="5" width="18" height="14" rx="2" />
                      <circle cx="9" cy="11" r="1.6" />
                      <path d="m21 16-4.5-4.5L9 19" />
                    </svg>
                  }
                />
              ) : null}
            </div>
          </section>
        );

      case "photo_gallery":
      case "featured_video":
      case "faq":
        return null;

      default:
        return null;
    }
  }

  const vaultCtaHref = primaryHref || `/@${page.username}/vault`;
  const eventsCtaHref = secondaryHref || "#upcoming-events";

  return (
    <main className="bg-background">
      <section className="relative overflow-hidden bg-ink text-paper">
        {media.coverUrl ? (
          <div className="absolute inset-0">
            <Media
              src={media.coverUrl}
              alt={hostCoverAlt(page.display_name)}
              className="h-full w-full object-cover opacity-40 padeya-hero-media"
              priority
              sizes="hero"
            />
          </div>
        ) : null}
        <div aria-hidden className="padeya-legacy-hero-gradient pointer-events-none absolute inset-0" />
        <div aria-hidden className="padeya-legacy-radar pointer-events-none absolute inset-0" />
        <div aria-hidden className="padeya-legacy-particles pointer-events-none absolute inset-0" />
        <div
          aria-hidden
          className="padeya-legacy-glow padeya-legacy-glow--a pointer-events-none absolute -left-16 top-10 h-56 w-56"
        />
        <div
          aria-hidden
          className="padeya-legacy-glow padeya-legacy-glow--b pointer-events-none absolute -right-10 bottom-8 h-64 w-64"
        />
        <div
          aria-hidden
          className="padeya-legacy-glow padeya-legacy-glow--c pointer-events-none absolute left-1/3 top-1/4 h-40 w-40"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-gradient-to-b from-ink/55 via-ink/70 to-ink"
        />

        <Container
          width="profile"
          className="relative flex min-h-[68vh] flex-col justify-between gap-8 py-10 sm:min-h-[72vh] sm:py-12 lg:py-14"
        >
          {/* Top — badges */}
          <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
            {page.verified ? <Badge tone="accent">Verified host</Badge> : null}
            <LegacyTierBadge tier={tierLabel} />
            {location ? (
              <Badge tone="outline" className="border-paper/25 text-paper/80">
                {location}
              </Badge>
            ) : null}
            {settings?.host_type_slug ? (
              <Badge tone="outline" className="border-paper/25 capitalize text-paper/80">
                {settings.host_type_slug.replace(/-/g, " ")}
              </Badge>
            ) : null}
          </div>

          {/* Center — identity */}
          <div className="mx-auto flex w-full max-w-3xl flex-col items-center gap-5 text-center">
            <div className="relative h-32 w-32 shrink-0 overflow-hidden rounded-full border-2 border-accent bg-ink shadow-[var(--shadow-glow)] sm:h-40 sm:w-40">
              {media.avatarUrl ? (
                <Media
                  src={media.avatarUrl}
                  alt={hostAvatarAlt(page.display_name)}
                  className="h-full w-full object-cover"
                  sizes="avatarLg"
                  loading="eager"
                />
              ) : (
                <span className="flex h-full w-full items-center justify-center text-4xl font-extrabold text-accent sm:text-5xl">
                  {page.display_name.slice(0, 1).toUpperCase()}
                </span>
              )}
            </div>
            <div className="space-y-3">
              <h1 className="text-balance break-words text-4xl font-extrabold tracking-tight [text-shadow:0_2px_28px_rgb(0_0_0_/_0.55)] sm:text-5xl md:text-6xl lg:text-[4rem] lg:leading-[1.05]">
                {page.display_name}
              </h1>
              <div className="flex flex-wrap items-center justify-center gap-2">
                <p className="text-base font-medium text-paper/75 sm:text-lg">
                  @{page.username}
                  {page.composite_score != null
                    ? ` · Legacy score ${Number(page.composite_score).toFixed(1)}`
                    : ""}
                </p>
                {page.shows_personal_gender &&
                page.gender_visible &&
                page.gender_short ? (
                  <GenderBadge
                    value={{
                      gender: page.gender ?? null,
                      gender_short: page.gender_short,
                      gender_label: page.gender_label ?? null,
                      gender_visible: page.gender_visible,
                    }}
                    className="border-paper/25 bg-paper/10 text-paper"
                  />
                ) : null}
              </div>
              <p className="mx-auto max-w-2xl text-base leading-relaxed text-paper/75 sm:text-lg">
                {tagline || (bio.length > 160 ? `${bio.slice(0, 160).trim()}…` : bio)}
              </p>
              {page.verified ? (
                <p className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary">
                  <span aria-hidden>✓</span> Verified on Pàdéyá
                </p>
              ) : null}
            </div>

            {/* CTA group */}
            <div className="flex w-full max-w-2xl flex-col items-center gap-3">
              {hostCtas.banner ? (
                <>
                  <div className="flex w-full flex-col items-center gap-3 rounded-[var(--radius-lg)] border border-paper/25 bg-ink/40 px-5 py-5 backdrop-blur-sm">
                    <p className="text-sm font-semibold text-paper/90">
                      {hostCtas.banner}
                    </p>
                    {hostCtas.primary ? (
                      <Link href={hostCtas.primary.href} className="inline-flex">
                        <Button type="button" size="lg" className="padeya-btn-micro">
                          {hostCtas.primary.label}
                        </Button>
                      </Link>
                    ) : null}
                  </div>
                  <Button
                    type="button"
                    size="lg"
                    variant="outline-dark"
                    onClick={() => void onShare()}
                    className="padeya-btn-micro"
                  >
                    Share
                  </Button>
                </>
              ) : (
                <>
                  {page.follow_enabled && hostCtas.showFollow ? (
                    <HostFollowControls
                      hostId={page.host_id}
                      hostSlug={page.username}
                      hostDisplayName={page.display_name}
                      loginNextPath={page.share_path}
                      onFollowDelta={(delta) => setFollowDelta((d) => d + delta)}
                      onError={(message) => setShareNote(message)}
                    />
                  ) : null}
                  <div className="flex w-full flex-wrap items-center justify-center gap-2.5">
                    <Button
                      type="button"
                      size="lg"
                      variant="outline-dark"
                      onClick={() => void onShare()}
                      className="padeya-btn-micro"
                    >
                      Share
                    </Button>
                    <CtaLink href={vaultCtaHref}>
                      <Button type="button" size="lg" variant="outline-dark" className="padeya-btn-micro">
                        {settings?.primary_cta_label && primaryHref
                          ? settings.primary_cta_label
                          : "Visit Vault"}
                      </Button>
                    </CtaLink>
                    <CtaLink href={eventsCtaHref}>
                      <Button type="button" size="lg" variant="outline-dark" className="padeya-btn-micro">
                        {settings?.secondary_cta_label && secondaryHref
                          ? settings.secondary_cta_label
                          : "View Events"}
                      </Button>
                    </CtaLink>
                    {hostCtas.showMessage ? (
                      <StartMessageButton
                        hostId={page.host_id}
                        hostUsername={page.username}
                        label="Message Host"
                        variant="outline-dark"
                        size="lg"
                        returnPath={`/@${page.username}`}
                      />
                    ) : null}
                    {contactHref ? (
                      <CtaLink href={contactHref}>
                        <Button type="button" size="lg" variant="outline-dark" className="padeya-btn-micro">
                          Contact
                        </Button>
                      </CtaLink>
                    ) : null}
                    {bookHref ? (
                      <CtaLink href={bookHref}>
                        <Button type="button" size="lg" variant="outline-dark" className="padeya-btn-micro">
                          Book sponsorship
                        </Button>
                      </CtaLink>
                    ) : null}
                  </div>
                </>
              )}
              {shareNote ? (
                <p className="text-sm text-subtle-foreground" role="status">
                  {shareNote}
                </p>
              ) : null}
            </div>
          </div>

          {/* Bottom — stats */}
          <div
            className="flex flex-wrap justify-center gap-2.5 sm:gap-3"
            aria-label="Host stats"
          >
            <HeroStat label="Followers" value={formatCompact(followerCount)} />
            <HeroStat
              label="Events hosted"
              value={formatCompact(page.stats.events_hosted)}
            />
            <HeroStat
              label="Tickets sold"
              value={formatCompact(page.stats.tickets_sold)}
            />
            <HeroStat label="Avg rating" value={avg} />
            <HeroStat label="Legacy tier" value={page.legacy_status} />
          </div>
        </Container>
      </section>

      <Container width="profile" className="py-8 sm:py-10">
        {page.trust_note ? (
          <p className="mb-6 rounded-[var(--radius-md)] border border-border bg-surface-muted px-4 py-3 text-sm text-body">
            {page.trust_note}
          </p>
        ) : null}
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(280px,340px)] xl:grid-cols-[minmax(0,1fr)_minmax(300px,360px)] lg:gap-9 xl:gap-10">
          <div className="space-y-9 sm:space-y-10">{blocks.map(renderBlock)}</div>

          <aside className="lg:sticky lg:top-24 lg:self-start">
            <div className="overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)] divide-y divide-border dark:bg-surface-elevated dark:shadow-[var(--shadow)]">
              <SidebarSection eyebrow="Reputation" title="Host stats">
                <div className="grid grid-cols-2 gap-2.5">
                  <ReputationStat
                    label="Events hosted"
                    value={formatCompact(page.stats.events_hosted)}
                    highlight
                  />
                  <ReputationStat
                    label="Tickets sold"
                    value={formatCompact(page.stats.tickets_sold)}
                    highlight
                  />
                  <ReputationStat
                    label="Check-ins"
                    value={formatCompact(page.stats.verified_checkins)}
                    hint="QR-confirmed"
                  />
                  <ReputationStat
                    label="Avg rating"
                    value={avg}
                    hint="Verified only"
                    highlight
                  />
                  <ReputationStat
                    label="Followers"
                    value={formatCompact(followerCount)}
                  />
                  <ReputationStat label="Reviews" value={formatCompact(page.stats.review_count)} />
                  {(page.stats.merch_items_sold ?? 0) > 0 ? (
                    <ReputationStat
                      label="Merch sold"
                      value={formatCompact(page.stats.merch_items_sold ?? 0)}
                    />
                  ) : null}
                  {(page.stats.fans_collected_merch ?? 0) > 0 ? (
                    <ReputationStat
                      label="Merch fans"
                      value={formatCompact(page.stats.fans_collected_merch ?? 0)}
                    />
                  ) : null}
                </div>
                {(page.stats.merch_proof_summaries?.length ?? 0) > 0 ? (
                  <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
                    {page.stats.merch_proof_summaries!.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                ) : null}
              </SidebarSection>

              <SidebarSection eyebrow="Legacy tier" title={page.legacy_status}>
                <LegacyTierBadge tier={tierLabel} />
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {page.tier?.description ||
                    "Legacy tiers reward verified delivery, check-ins, reviews, and fan loyalty on Pàdéyá."}
                </p>
              </SidebarSection>

              <SidebarSection eyebrow="Vault" title="Exclusive fan content">
                <p className="text-sm leading-relaxed text-muted-foreground">
                  Locked drops for followers, ticket holders, and VIPs.
                </p>
                <Link href={`/@${page.username}/vault`} className="block">
                  <Button size="lg" className="w-full padeya-btn-micro">
                    Open Vault
                  </Button>
                </Link>
              </SidebarSection>

              {(settings?.sponsorship_available || sponsorPackages.length > 0) ? (
                <SidebarSection eyebrow="Sponsor" title="Brand packages">
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {settings?.sponsorship_note ||
                      "Book a package and put your brand next to verified nights."}
                  </p>
                  <a href="#sponsorship" className="block">
                    <Button size="lg" variant="secondary" className="w-full padeya-btn-micro">
                      View packages
                    </Button>
                  </a>
                </SidebarSection>
              ) : null}

              {(serviceAreas.length > 0 || page.upcoming_events.length > 0) ? (
                <SidebarSection eyebrow="Availability" title="Where they host">
                  {serviceAreas.length > 0 ? (
                    <ul className="flex flex-wrap gap-2">
                      {serviceAreas.slice(0, 6).map((area) => (
                        <li key={area}>
                          <Badge tone="neutral">{area}</Badge>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      {page.upcoming_events.length} upcoming event
                      {page.upcoming_events.length === 1 ? "" : "s"} on the calendar.
                    </p>
                  )}
                </SidebarSection>
              ) : null}

              {page.contact && page.contact.preference !== "none" ? (
                <SidebarSection eyebrow="Contact" title="Get in touch">
                  {page.contact.note ? (
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {page.contact.note}
                    </p>
                  ) : null}
                  {page.contact.public_email ? (
                    <a
                      href={`mailto:${page.contact.public_email}`}
                      className="block text-sm font-bold text-foreground underline-offset-2 hover:underline"
                    >
                      {page.contact.public_email}
                    </a>
                  ) : (
                    <a href="#contact" className="block">
                      <Button size="md" variant="secondary" className="w-full padeya-btn-micro">
                        Contact host
                      </Button>
                    </a>
                  )}
                </SidebarSection>
              ) : null}
            </div>
          </aside>
        </div>

        <footer className="mt-10 border-t border-border/80 pt-6 sm:mt-12 sm:pt-7">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-muted-foreground">
              Legacy Page · @{page.username} on Pàdéyá
            </p>
            <div className="flex flex-wrap gap-3 text-sm font-bold text-foreground">
              <Link
                href="/hosts"
                className="underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background"
              >
                Browse hosts
              </Link>
              <span className="text-border" aria-hidden>
                ·
              </span>
              <Link
                href="/events"
                className="underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background"
              >
                Discover events
              </Link>
            </div>
          </div>
        </footer>
      </Container>
    </main>
  );
}
