"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { TrackImpression } from "@/components/analytics/TrackImpression";
import { useAuth } from "@/components/auth/AuthProvider";
import { CompletedEventPublicView } from "@/components/events/completed/CompletedEventPublicView";
import { EventDetailRecommendationsRail } from "@/components/events/EventDetailRecommendationsRail";
import { EventFanConnectSection } from "@/components/fan-connect/EventFanConnectSection";
import { SponsorSaveButton } from "@/components/sponsor/SponsorSaveButton";
import { StartMessageButton } from "@/components/messaging/StartMessageButton";
import { EventRelatedSections } from "@/components/events/EventRelatedSections";
import { refundPolicyLabel } from "@/components/events/studio/policy-utils";
import { MarketplaceBreadcrumbs } from "@/components/layout/MarketplaceBreadcrumbs";
import {
  Button,
  Container,
  Media,
} from "@/components/ui";
import { RelatedVaultTeaserSection } from "@/components/vault/public/RelatedVaultTeaserSection";
import { useHostAffiliation } from "@/hooks/useHostAffiliation";
import { useUserRestrictions } from "@/hooks/useUserRestrictions";
import { eventPageCtaMode, eventPageCtas } from "@/lib/own-host-ctas";
import { eventCoverAlt } from "@/lib/seo/image-alt";
import { USER_RESTRICTION_ACTION_MESSAGE } from "@/lib/user-restrictions";
import {
  trackBuyTicketClick,
  trackHostProfileClick,
  trackPageView,
  trackRefundPolicyView,
  trackShareClick,
  trackTicketPanelView,
} from "@/lib/analytics";
import { cn } from "@/lib/cn";
import { citySlugFromName } from "@/lib/discovery/slugify";
import {
  downloadEventIcs,
  shareEventPage,
  ticketAvailability,
} from "@/lib/event-page";
import { formatPublicVenueDetail } from "@/lib/event-privacy";
import { formatDateTime, formatNgn } from "@/lib/format";
import { buildEventTrail } from "@/lib/marketplace-breadcrumbs";
import type { EventItem } from "@/lib/types/events";
import type { VaultCatalogCard } from "@/lib/types/vault";
import { fetchVaultRelatedToEvent } from "@/lib/vault-api";

import { EventAgendaSection } from "./EventAgendaSection";
import { EventDateBadge } from "./EventDateBadge";
import { EventDetailPanel, EventInfoTile } from "./EventDetailPanel";
import {
  EventAccessLogisticsSection,
  EventGuestPrepSection,
} from "./EventGuestInfoSections";
import { EventLineupSection } from "./EventLineupSection";
import { EventLocationPrivacyNotice } from "./EventLocationPrivacyNotice";
import { EventMerchSection } from "@/components/merch/EventMerchSection";
import { PromoteEventAmbassadors } from "./PromoteEventAmbassadors";
import { TicketTierList } from "./TicketTierList";

/** Maps / Places stay out of the initial event-detail chunk. */
const EventLocationMapCard = dynamic(
  () =>
    import("./EventLocationMapCard").then((m) => m.EventLocationMapCard),
  {
    ssr: false,
    loading: () => (
      <div
        className="min-h-[180px] animate-pulse rounded-[var(--radius-xl)] bg-surface-inset"
        aria-hidden
      />
    ),
  },
);

/** Gallery may embed YouTube — keep player JS off the critical path. */
const EventGallery = dynamic(
  () => import("./EventGallery").then((m) => m.EventGallery),
  {
    loading: () => (
      <div
        className="min-h-[120px] animate-pulse rounded-[var(--radius-xl)] bg-surface-inset"
        aria-hidden
      />
    ),
  },
);


export function EventPublicView({
  event,
  related = [],
  referralCode = "",
  previewMode = false,
  onGetTicketsClick,
}: {
  event: EventItem;
  related?: EventItem[];
  referralCode?: string;
  previewMode?: boolean;
  onGetTicketsClick?: () => void;
}) {
  const { user } = useAuth();
  const [shareNote, setShareNote] = useState<string | null>(null);
  const [relatedVaultData, setRelatedVaultData] = useState<VaultCatalogCard[]>([]);
  const relatedVault = previewMode ? [] : relatedVaultData;
  const checkoutHref = `/events/${event.slug}/checkout${referralCode ? `?ref=${referralCode}` : ""}`;
  const hostVaultHref = event.host_slug ? `/u/${event.host_slug}/vault` : null;
  const { affiliated: isOwnHost } = useHostAffiliation({
    hostId: event.host_id,
    hostSlug: event.host_slug,
  });
  const { hasAny } = useUserRestrictions();
  const checkoutBlocked = hasAny([
    "cannot_checkout",
    "cannot_buy_tickets",
  ]);
  const eventCtas = eventPageCtas(eventPageCtaMode(isOwnHost), event.id);
  const manageEventHref =
    eventCtas.primary?.href && !eventCtas.showBuyTicket
      ? eventCtas.primary.href
      : `/host/events/${event.id}`;

  useEffect(() => {
    if (previewMode) return;
    trackPageView({
      path: `/events/${event.slug}`,
      targetEventId: event.id,
      hostId: event.host_id,
    });
  }, [event.id, event.slug, event.host_id, previewMode]);

  useEffect(() => {
    if (previewMode) return;
    let active = true;
    void fetchVaultRelatedToEvent(event.id)
      .then((rows) => {
        if (active) setRelatedVaultData(rows);
      })
      .catch(() => {
        if (active) setRelatedVaultData([]);
      });
    return () => {
      active = false;
    };
  }, [event.id, previewMode]);

  const venueLine = formatPublicVenueDetail(event);
  const hasTickets = (event.ticket_types ?? []).length > 0;
  const whenLong = useMemo(() => {
    const start = new Date(event.start_datetime);
    const end = event.end_datetime ? new Date(event.end_datetime) : null;
    const startLabel = start.toLocaleString("en-NG", {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
    if (!end || Number.isNaN(end.getTime())) return startLabel;
    const endTime = end.toLocaleString("en-NG", {
      hour: "numeric",
      minute: "2-digit",
    });
    return `${startLabel} – ${endTime}`;
  }, [event.start_datetime, event.end_datetime]);

  const minPrice = useMemo(() => {
    const prices = (event.ticket_types ?? [])
      .map((t) => Number(t.price))
      .filter((n) => Number.isFinite(n));
    if (!prices.length) return null;
    const min = Math.min(...prices);
    return min === 0 ? "Free" : `From ${formatNgn(min)}`;
  }, [event]);

  const anyTicketOpen = (event.ticket_types ?? []).some(
    (t) => !ticketAvailability(t).closed,
  );
  const isCompleted = event.status === "completed";
  const canBuyTickets =
    !previewMode && !isCompleted && hasTickets && anyTicketOpen;

  if (isCompleted) {
    return (
      <CompletedEventPublicView
        event={event}
        related={related}
        previewMode={previewMode}
      />
    );
  }

  function onCheckoutIntent() {
    trackBuyTicketClick({
      targetEventId: event.id,
      hostId: event.host_id,
    });
    onGetTicketsClick?.();
  }

  async function onShare() {
    trackShareClick({
      targetEventId: event.id,
      hostId: event.host_id,
    });
    try {
      const result = await shareEventPage(event);
      setShareNote(result === "copied" ? "Link copied" : "Shared");
      window.setTimeout(() => setShareNote(null), 2200);
    } catch {
      setShareNote("Unable to share");
      window.setTimeout(() => setShareNote(null), 2200);
    }
  }

  const hostHref = event.host_slug
    ? `/u/${encodeURIComponent(event.host_slug)}`
    : "/hosts";

  const locationHubHref = (() => {
    const loc = event.location;
    if (loc?.kind && loc?.slug) {
      return `/events/${loc.kind}/${encodeURIComponent(loc.slug)}`;
    }
    if (event.city) {
      const citySlug = event.city
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      if (citySlug) return `/events/city/${citySlug}`;
    }
    return null;
  })();

  return (
    <main className="min-w-0 overflow-x-clip bg-[linear-gradient(180deg,var(--surface)_0%,var(--muted)_42%,var(--surface)_100%)] pb-28 lg:pb-14">
      {!previewMode ? (
        <MarketplaceBreadcrumbs
          items={buildEventTrail({
            title: event.title,
            slug: event.slug,
            city: event.city,
            citySlug: event.city ? citySlugFromName(event.city) : null,
            categoryName: event.category?.name,
            categorySlug: event.category?.slug,
            location: event.location
              ? {
                  kind: event.location.kind,
                  slug: event.location.slug,
                  name: event.location.name,
                  ancestors: event.location.ancestors,
                }
              : null,
          })}
        />
      ) : null}
      {previewMode ? (
        <div className="border-b border-border bg-ink px-4 py-3 text-center text-sm text-paper">
          <p className="font-semibold">Guest preview</p>
          <p className="mt-0.5 text-subtle-foreground">
            This is how buyers see your event. It is not public until Pàdéyá approves it.
          </p>
        </div>
      ) : null}

      <section className="relative h-[42vh] min-h-[240px] overflow-hidden bg-ink sm:h-[52vh] sm:min-h-[320px]">
        {event.banner_url ? (
          <>
            <Media
              src={event.banner_url}
              alt={eventCoverAlt(event.title)}
              className="padeya-hero-media absolute inset-0 h-full w-full object-cover opacity-85"
              priority
              sizes="hero"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-background via-ink/30 to-ink/55" />
          </>
        ) : (
          <div aria-hidden className="padeya-hero-glow absolute inset-0" />
        )}
      </section>

      <Container className="relative -mt-20 space-y-8 pb-6 sm:-mt-24 sm:space-y-10">
        <header className="padeya-hero-brand overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow)] dark:bg-surface-elevated">
          <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_220px]">
            <div className="p-5 sm:p-7 lg:p-8">
              <div className="flex min-w-0 gap-4 sm:gap-5">
                <EventDateBadge date={event.start_datetime} />
                <div className="min-w-0 space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    {event.featured ? (
                      <span className="rounded-[var(--radius-sm)] bg-accent px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wide text-primary-foreground">
                        Featured
                      </span>
                    ) : null}
                    {event.category ? (
                      <Link
                        href={`/events/c/${event.category.slug}`}
                        className="rounded-[var(--radius-sm)] bg-surface-muted px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-foreground transition-colors hover:bg-muted"
                      >
                        {event.category.name}
                      </Link>
                    ) : null}
                    {event.vibe ? (
                      <span className="text-xs font-medium text-muted-foreground">
                        {event.vibe}
                      </span>
                    ) : null}
                  </div>
                  <h1 className="text-balance text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl lg:text-[2.75rem] lg:leading-[1.05]">
                    {event.title}
                  </h1>
                  {event.short_tagline ? (
                    <p className="max-w-2xl text-base leading-relaxed text-muted-foreground">
                      {event.short_tagline}
                    </p>
                  ) : null}
                  <div className="flex flex-col gap-1.5 pt-1 text-sm text-muted-foreground sm:text-[15px]">
                    <p>
                      <span className="font-semibold text-foreground">When · </span>
                      {formatDateTime(event.start_datetime)}
                      {event.doors_open_datetime
                        ? ` · Doors ${formatDateTime(event.doors_open_datetime)}`
                        : ""}
                    </p>
                    <p>
                      <span className="font-semibold text-foreground">Where · </span>
                      {locationHubHref ? (
                        <Link
                          href={locationHubHref}
                          className="underline decoration-accent underline-offset-2"
                        >
                          {venueLine || "Location TBA"}
                        </Link>
                      ) : (
                        venueLine || "Location TBA"
                      )}
                    </p>
                    {event.host_display_name ? (
                      <p>
                        <span className="font-semibold text-foreground">Host · </span>
                        <Link
                          href={hostHref}
                          className="underline decoration-accent underline-offset-2"
                          onClick={() =>
                            trackHostProfileClick({
                              targetEventId: event.id,
                              hostId: event.host_id,
                            })
                          }
                        >
                          {event.host_display_name}
                        </Link>
                      </p>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>
            <div className="flex flex-col justify-between gap-3 border-t border-border bg-muted/70 p-5 sm:flex-row sm:items-center lg:flex-col lg:border-l lg:border-t-0 lg:p-6">
              <div>
                <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
                  Tickets
                </p>
                <p className="mt-1 text-2xl font-extrabold tracking-tight text-foreground">
                  {minPrice ?? "See tiers"}
                </p>
              </div>
              <div className="flex flex-wrap gap-2 lg:flex-col lg:items-stretch">
                <SponsorSaveButton itemType="event" itemId={event.id} />
                <Button type="button" variant="secondary" size="sm" onClick={() => void onShare()}>
                  {shareNote ?? "Share"}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => downloadEventIcs(event, venueLine || "TBA")}
                >
                  Calendar
                </Button>
                {!previewMode && isOwnHost ? (
                  <Link href={manageEventHref}>
                    <Button size="sm" className="w-full">
                      Manage event
                    </Button>
                  </Link>
                ) : canBuyTickets ? (
                  checkoutBlocked ? (
                    <Button
                      size="sm"
                      className="w-full"
                      disabled
                      title={USER_RESTRICTION_ACTION_MESSAGE}
                    >
                      Get tickets
                    </Button>
                  ) : (
                    <Link href={checkoutHref} onClick={onCheckoutIntent}>
                      <Button size="sm" className="w-full">
                        Get tickets
                      </Button>
                    </Link>
                  )
                ) : null}
              </div>
            </div>
          </div>
        </header>

        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px] xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="min-w-0 space-y-7 sm:space-y-8">
            <EventLocationPrivacyNotice event={event} />

            <EventDetailPanel title="About this event">
              <p className="whitespace-pre-wrap text-base leading-[1.75] text-body">
                {event.description}
              </p>
            </EventDetailPanel>

            <EventGuestPrepSection event={event} />
            <EventGallery event={event} />

            <EventDetailPanel title="Ticket information">
              <TicketTierList event={event} />
              <p className="mt-4 text-xs text-muted-foreground">
                Tickets are issued only after secure payment confirmation.
              </p>
            </EventDetailPanel>

            <EventMerchSection
              eventId={event.id}
              eventSlug={event.slug}
              eventTitle={event.title}
              hostId={event.host_id}
              hostName={event.host_display_name}
              hostSlug={event.host_slug}
              referralCode={referralCode || undefined}
              previewMode={previewMode}
              ownHostMode={!eventCtas.showBuyMerchCheckout}
            />

            <EventLocationMapCard event={event} />

            <EventDetailPanel
              title="Event calendar"
              action={
                <span
                  className={cn(
                    "text-xs font-extrabold uppercase tracking-wide",
                    anyTicketOpen
                      ? "text-[color:var(--brand-green-hover)]"
                      : "text-danger",
                  )}
                >
                  {anyTicketOpen ? "Open" : "Closed"}
                </span>
              }
            >
              <p className="text-base font-semibold text-foreground">{whenLong}</p>
              {event.timezone ? (
                <p className="mt-1 text-sm text-muted-foreground">Timezone: {event.timezone}</p>
              ) : null}
            </EventDetailPanel>

            <EventAgendaSection items={event.agenda_items ?? []} />
            <EventLineupSection people={event.people ?? []} />
            <EventAccessLogisticsSection event={event} />

            <TrackImpression
              targetEventId={event.id}
              hostId={event.host_id}
              listContext="event_detail"
              trackCardImpression={false}
              onImpression={() => {
                trackRefundPolicyView({
                  targetEventId: event.id,
                  hostId: event.host_id,
                });
              }}
            >
              <EventDetailPanel title="Policies & entry">
                <div className="grid gap-3 sm:grid-cols-2 sm:gap-4">
                  <EventInfoTile label="Refund policy">
                    <p className="font-semibold">
                      {refundPolicyLabel(
                        event.refund_policy_type || event.refund_policy,
                      )}
                    </p>
                    {event.refund_policy_text ? (
                      <p className="whitespace-pre-wrap text-muted-foreground">
                        {event.refund_policy_text}
                      </p>
                    ) : null}
                  </EventInfoTile>
                  {event.cancellation_policy ? (
                    <EventInfoTile label="Cancellation">
                      <p className="whitespace-pre-wrap">
                        {event.cancellation_policy}
                      </p>
                    </EventInfoTile>
                  ) : null}
                  <EventInfoTile label="Entry">
                    <ul className="space-y-1">
                      {event.age_restriction ? (
                        <li>
                          <span className="font-semibold">Age:</span>{" "}
                          {event.age_restriction}
                        </li>
                      ) : null}
                      {event.id_required ? (
                        <li>Valid ID required at the door</li>
                      ) : null}
                      {event.entry_requirements ? (
                        <li className="whitespace-pre-wrap">
                          {event.entry_requirements}
                        </li>
                      ) : null}
                      {event.door_sales_allowed === false ? (
                        <li>No door sales</li>
                      ) : null}
                      {event.re_entry_allowed === false ? (
                        <li>No re-entry</li>
                      ) : null}
                    </ul>
                  </EventInfoTile>
                  {event.safety_notice ? (
                    <EventInfoTile label="Safety">
                      <p className="whitespace-pre-wrap">
                        {event.safety_notice}
                      </p>
                    </EventInfoTile>
                  ) : null}
                </div>
              </EventDetailPanel>
            </TrackImpression>

            <EventDetailPanel title="Why book on Pàdéyá">
              <p className="text-sm leading-relaxed text-muted-foreground sm:text-base">
                Secure checkout · QR tickets after confirmation ·
                staff check-in at the door.
              </p>
            </EventDetailPanel>

            {!previewMode && relatedVault.length > 0 && event.host_slug ? (
              <RelatedVaultTeaserSection
                items={relatedVault}
                username={event.host_slug}
                hostId={event.host_id}
                sourcePage="event_detail"
                listContext="event_detail"
                title="Exclusive Vault drops"
                description="Unlock recap content after the event — teasers only until you have access."
                vaultHref={hostVaultHref || undefined}
                ctaLabel="Browse host Vault"
              />
            ) : null}

            {!previewMode ? (
              <EventFanConnectSection event={event} previewMode={previewMode} />
            ) : null}

            {!previewMode ? (
              user ? (
                <EventDetailRecommendationsRail event={event} />
              ) : (
                <EventRelatedSections event={event} allEvents={related} />
              )
            ) : null}
          </div>

          <aside className="min-w-0 space-y-4 lg:sticky lg:top-24 lg:self-start">
            <TrackImpression
              targetEventId={event.id}
              hostId={event.host_id}
              listContext="event_detail"
              trackCardImpression={false}
              onImpression={() => {
                trackTicketPanelView({
                  targetEventId: event.id,
                  hostId: event.host_id,
                });
              }}
            >
              <div className="rounded-[var(--radius-xl)] border border-ink bg-ink p-5 text-paper shadow-[var(--shadow)] sm:p-6">
                <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-accent">
                  {isOwnHost ? "Host tools" : "Get tickets"}
                </p>
                <p className="mt-2 text-3xl font-extrabold tracking-tight">
                  {minPrice ?? "See tiers"}
                </p>
                <p className="mt-2 text-sm text-subtle-foreground">
                  {formatDateTime(event.start_datetime)}
                </p>
                <p className="mt-1 text-sm text-subtle-foreground">{venueLine || "Location TBA"}</p>
                {referralCode ? (
                  <p className="mt-2 text-xs text-subtle-foreground">
                    Referral:{" "}
                    <span className="font-semibold text-paper">{referralCode}</span>
                  </p>
                ) : null}
                <div className="mt-5">
                  {previewMode ? (
                    <Button className="w-full" size="lg" disabled>
                      Preview only
                    </Button>
                  ) : isOwnHost || !eventCtas.showBuyTicket ? (
                    <Link href={manageEventHref} className="block">
                      <Button className="w-full" size="lg">
                        {eventCtas.primary?.label ?? "Manage event"}
                      </Button>
                    </Link>
                  ) : hasTickets && anyTicketOpen ? (
                    checkoutBlocked ? (
                      <Button
                        className="w-full"
                        size="lg"
                        disabled
                        title={USER_RESTRICTION_ACTION_MESSAGE}
                      >
                        Get tickets
                      </Button>
                    ) : (
                      <Link
                        href={checkoutHref}
                        className="block"
                        onClick={onCheckoutIntent}
                      >
                        <Button className="w-full" size="lg">
                          Get tickets
                        </Button>
                      </Link>
                    )
                  ) : (
                    <Button className="w-full" size="lg" disabled>
                      {hasTickets ? "Booking closed" : "Tickets soon"}
                    </Button>
                  )}
                </div>
                <ul className="mt-4 space-y-2 border-t border-paper/15 pt-4 text-xs text-subtle-foreground">
                  <li>Secure checkout</li>
                  <li>Tickets issued after confirmation</li>
                  <li>QR ready for door check-in</li>
                </ul>
              </div>
            </TrackImpression>

            <PromoteEventAmbassadors event={event} previewMode={previewMode} />

            <div className="rounded-[var(--radius-xl)] border border-border bg-card p-5 shadow-[var(--shadow-soft)] dark:bg-surface-elevated dark:shadow-[var(--shadow)]">
              <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
                Location
              </p>
              <p className="mt-2 text-base font-extrabold text-heading">
                {venueLine || event.public_location_label || "Location TBA"}
              </p>
              {event.location_privacy_message ? (
                <p className="mt-2 text-sm font-medium text-body">
                  {event.location_privacy_message}
                </p>
              ) : null}
              {event.map_open_url ? (
                <a
                  href={event.map_open_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 inline-block text-xs font-extrabold uppercase tracking-wide text-foreground underline decoration-accent underline-offset-4"
                >
                  {event.location_map_mode === "exact"
                    ? "Open in Google Maps"
                    : "View area in Maps"}
                </a>
              ) : null}
            </div>

            <div className="rounded-[var(--radius-xl)] border border-border bg-card p-5 shadow-[var(--shadow-soft)] dark:bg-surface-elevated dark:shadow-[var(--shadow)]">
              <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
                Organizer
              </p>
              <div className="mt-3 flex items-center gap-3">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-ink text-lg font-extrabold text-accent">
                  {(event.host_display_name ?? "P").slice(0, 1).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-lg font-extrabold text-foreground">
                    {event.host_display_name ?? "Pàdéyá host"}
                  </p>
                  <p className="text-sm text-muted-foreground">Verified on Pàdéyá</p>
                </div>
              </div>
              {!previewMode ? (
                <div className="mt-4 grid gap-2">
                  <Link
                    href={hostHref}
                    onClick={() => {
                      trackHostProfileClick({
                        targetEventId: event.id,
                        hostId: event.host_id,
                      });
                    }}
                  >
                    <Button variant="secondary" className="w-full">
                      View Legacy Page
                    </Button>
                  </Link>
                  {hostVaultHref ? (
                    <Link href={hostVaultHref}>
                      <Button variant="secondary" className="w-full">
                        Host Vault
                      </Button>
                    </Link>
                  ) : null}
                  {event.host_id && !isOwnHost ? (
                    <StartMessageButton
                      hostId={event.host_id}
                      hostUsername={event.host_slug || undefined}
                      relatedEventId={event.id}
                      label="Ask host a question"
                      variant="secondary"
                      returnPath={`/events/${event.slug}`}
                    />
                  ) : null}
                </div>
              ) : null}
            </div>
          </aside>
        </div>
      </Container>

      {hasTickets || isOwnHost ? (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur dark:bg-surface-elevated/95 lg:hidden">
          <Container className="flex items-center gap-3 !px-0">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-bold text-foreground">{event.title}</p>
              <p className="truncate text-xs text-muted-foreground">
                {isOwnHost ? "Your event" : minPrice ?? "Tickets"}
              </p>
            </div>
            {previewMode ? (
              <Button className="shrink-0 whitespace-nowrap" disabled>
                Preview only
              </Button>
            ) : isOwnHost || !eventCtas.showBuyTicket ? (
              <Link href={manageEventHref} className="shrink-0">
                <Button className="whitespace-nowrap">
                  {eventCtas.primary?.label ?? "Manage event"}
                </Button>
              </Link>
            ) : anyTicketOpen ? (
              checkoutBlocked ? (
                <Button
                  className="shrink-0 whitespace-nowrap"
                  disabled
                  title={USER_RESTRICTION_ACTION_MESSAGE}
                >
                  Get tickets
                </Button>
              ) : (
                <Link
                  href={checkoutHref}
                  className="shrink-0"
                  onClick={onCheckoutIntent}
                >
                  <Button className="whitespace-nowrap">Get tickets</Button>
                </Link>
              )
            ) : (
              <Button className="shrink-0 whitespace-nowrap" disabled>
                Closed
              </Button>
            )}
          </Container>
        </div>
      ) : null}
    </main>
  );
}
