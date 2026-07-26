"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { CompletedEventDiscoveryCTA } from "@/components/events/completed/CompletedEventDiscoveryCTA";
import { CompletedEventMemoriesPreview } from "@/components/events/completed/CompletedEventMemoriesPreview";
import { CompletedEventReviews } from "@/components/events/completed/CompletedEventReviews";
import { CompletedEventSidebar } from "@/components/events/completed/CompletedEventSidebar";
import { CompletedEventTicketHistory } from "@/components/events/completed/CompletedEventTicketHistory";
import { EventDetailRecommendationsRail } from "@/components/events/EventDetailRecommendationsRail";
import { EventRelatedSections } from "@/components/events/EventRelatedSections";
import { MarketplaceBreadcrumbs } from "@/components/layout/MarketplaceBreadcrumbs";
import { HostFollowControls } from "@/components/hosts/HostFollowControls";
import { StartMessageButton } from "@/components/messaging/StartMessageButton";
import { Button, Container, Media } from "@/components/ui";
import { RelatedVaultTeaserSection } from "@/components/vault/public/RelatedVaultTeaserSection";
import { useHostAffiliation } from "@/hooks/useHostAffiliation";
import {
  trackHostProfileClick,
  trackPageView,
  trackShareClick,
} from "@/lib/analytics";
import { citySlugFromName } from "@/lib/discovery/slugify";
import {
  completedEventMetaLine,
  memoriesHref,
} from "@/lib/events/completed-event";
import { downloadEventIcs, shareEventPage } from "@/lib/event-page";
import { formatPublicVenueDetail } from "@/lib/event-privacy";
import { formatDate, formatDateTime } from "@/lib/format";
import { buildEventTrail } from "@/lib/marketplace-breadcrumbs";
import { fetchMemoryByEventSlug } from "@/lib/memories-api";
import { eventPageCtaMode, eventPageCtas } from "@/lib/own-host-ctas";
import { eventCoverAlt } from "@/lib/seo/image-alt";
import type { EventItem } from "@/lib/types/events";
import type { EventMemory } from "@/lib/types/memories";
import type { VaultCatalogCard } from "@/lib/types/vault";
import { fetchVaultRelatedToEvent } from "@/lib/vault-api";

import { EventAgendaSection } from "../EventAgendaSection";
import { EventDateBadge } from "../EventDateBadge";
import { EventDetailPanel } from "../EventDetailPanel";
import {
  EventAccessLogisticsSection,
  EventGuestPrepSection,
} from "../EventGuestInfoSections";
import { EventLineupSection } from "../EventLineupSection";
import { EventLocationPrivacyNotice } from "../EventLocationPrivacyNotice";

const EventLocationMapCard = dynamic(
  () =>
    import("../EventLocationMapCard").then((m) => m.EventLocationMapCard),
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

const EventGallery = dynamic(
  () => import("../EventGallery").then((m) => m.EventGallery),
  {
    loading: () => (
      <div
        className="min-h-[120px] animate-pulse rounded-[var(--radius-xl)] bg-surface-inset"
        aria-hidden
      />
    ),
  },
);

/**
 * Dedicated completed-event experience: memories, recap, host follow, discovery.
 * Does not render purchase / checkout / quantity UI.
 */
export function CompletedEventPublicView({
  event,
  related = [],
  previewMode = false,
}: {
  event: EventItem;
  related?: EventItem[];
  previewMode?: boolean;
}) {
  const { user } = useAuth();
  const [shareNote, setShareNote] = useState<string | null>(null);
  const [memory, setMemory] = useState<EventMemory | null>(null);
  const [memoryLoading, setMemoryLoading] = useState(true);
  const [relatedVaultData, setRelatedVaultData] = useState<VaultCatalogCard[]>(
    [],
  );
  const relatedVault = previewMode ? [] : relatedVaultData;

  const { affiliated: isOwnHost } = useHostAffiliation({
    hostId: event.host_id,
    hostSlug: event.host_slug,
  });
  const eventCtas = eventPageCtas(eventPageCtaMode(isOwnHost), event.id);
  const manageEventHref =
    eventCtas.primary?.href && !eventCtas.showBuyTicket
      ? eventCtas.primary.href
      : `/host/events/${event.id}/memory`;

  useEffect(() => {
    if (previewMode) return;
    trackPageView({
      path: `/events/${event.slug}`,
      targetEventId: event.id,
      hostId: event.host_id,
    });
  }, [event.id, event.slug, event.host_id, previewMode]);

  useEffect(() => {
    let active = true;
    setMemoryLoading(true);
    void fetchMemoryByEventSlug(event.slug)
      .then((data) => {
        if (active) setMemory(data);
      })
      .catch(() => {
        if (active) setMemory(null);
      })
      .finally(() => {
        if (active) setMemoryLoading(false);
      });
    return () => {
      active = false;
    };
  }, [event.slug]);

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
  const hostHref = event.host_slug
    ? `/u/${encodeURIComponent(event.host_slug)}`
    : "/hosts";
  const hostVaultHref = event.host_slug ? `/u/${event.host_slug}/vault` : null;
  const memoriesPath = memoriesHref(event.slug);
  const metaLine = useMemo(() => completedEventMetaLine(event), [event]);
  const memoryCount = memory?.counts?.memory_count ?? 0;

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

  const hasGallery = (event.media ?? []).some(
    (m) => m.media_type === "gallery" && m.url?.trim(),
  );

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
          <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_240px]">
            <div className="p-5 sm:p-7 lg:p-8">
              <div className="flex min-w-0 gap-4 sm:gap-5">
                <EventDateBadge date={event.start_datetime} />
                <div className="min-w-0 space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-[var(--radius-sm)] bg-info-surface px-2.5 py-1 text-[11px] font-extrabold uppercase tracking-wide text-info-foreground ring-1 ring-inset ring-info/45">
                      Past event
                    </span>
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
                  </div>
                  <h1 className="text-balance text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl lg:text-[2.75rem] lg:leading-[1.05]">
                    {event.title}
                  </h1>
                  <p className="text-sm text-muted-foreground sm:text-[15px]">
                    {formatDate(event.start_datetime)}
                    {event.city ? ` · ${event.city}` : ""}
                  </p>
                  {metaLine ? (
                    <p className="max-w-2xl text-base leading-relaxed text-muted-foreground">
                      {metaLine}
                    </p>
                  ) : null}
                  {event.host_display_name ? (
                    <p className="text-sm text-muted-foreground sm:text-[15px]">
                      <span className="font-semibold text-foreground">
                        Hosted by{" "}
                      </span>
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
            <div className="flex flex-col justify-between gap-3 border-t border-border bg-muted/70 p-5 sm:flex-row sm:items-center lg:flex-col lg:border-l lg:border-t-0 lg:p-6">
              <div>
                <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
                  Past event
                </p>
                <p className="mt-1 text-2xl font-extrabold tracking-tight text-foreground">
                  {memoryCount > 0
                    ? `${memoryCount} memories`
                    : "Memories"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatDateTime(event.start_datetime)}
                </p>
              </div>
              <div className="flex flex-wrap gap-2 lg:flex-col lg:items-stretch">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void onShare()}
                >
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
                      Manage memories
                    </Button>
                  </Link>
                ) : (
                  <Link href={memoriesPath}>
                    <Button size="sm" className="w-full">
                      View memories
                    </Button>
                  </Link>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Mobile memories CTA — above fold, no purchase footer */}
        <div className="rounded-[var(--radius-xl)] border border-ink bg-ink p-4 text-paper lg:hidden">
          <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-accent">
            Event ended
          </p>
          <p className="mt-1 text-sm text-subtle-foreground">
            {formatDate(event.start_datetime)}
            {memoryCount > 0 ? ` · ${memoryCount} memories` : ""}
          </p>
          <Link href={memoriesPath} className="mt-3 block">
            <Button className="w-full" size="lg">
              View memories
            </Button>
          </Link>
        </div>

        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px] xl:grid-cols-[minmax(0,1.95fr)_minmax(0,1fr)]">
          <div className="min-w-0 space-y-7 sm:space-y-8">
            <EventLocationPrivacyNotice event={event} />

            <EventDetailPanel title="About this event">
              {memory?.host_recap_note ? (
                <p className="mb-4 whitespace-pre-wrap text-base leading-[1.75] text-foreground">
                  {memory.host_recap_note}
                </p>
              ) : null}
              <p className="whitespace-pre-wrap text-base leading-[1.75] text-body">
                {event.description}
              </p>
            </EventDetailPanel>

            <CompletedEventMemoriesPreview
              event={event}
              memory={memory}
              loading={memoryLoading}
              previewMode={previewMode}
              isOwnHost={isOwnHost}
            />

            <CompletedEventReviews memory={memory} />

            {(event.what_to_expect ||
              (event.agenda_items ?? []).length > 0 ||
              (event.people ?? []).length > 0) && (
              <EventDetailPanel title="Highlights">
                {event.what_to_expect ? (
                  <p className="whitespace-pre-wrap text-base leading-relaxed text-body">
                    {event.what_to_expect}
                  </p>
                ) : null}
                <div className="mt-4 space-y-6">
                  <EventAgendaSection items={event.agenda_items ?? []} />
                  <EventLineupSection people={event.people ?? []} />
                </div>
              </EventDetailPanel>
            )}

            <EventGuestPrepSection event={event} />
            <EventAccessLogisticsSection event={event} />

            <EventLocationMapCard event={event} />

            <CompletedEventTicketHistory event={event} />

            {hasGallery ? (
              <div className="space-y-2">
                <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
                  Official event media
                </p>
                <EventGallery event={event} />
              </div>
            ) : null}

            <div className="rounded-[var(--radius-xl)] border border-border bg-card p-5 shadow-[var(--shadow-soft)] dark:bg-surface-elevated">
              <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
                Hosted by
              </p>
              <div className="mt-3 flex items-center gap-3">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-ink text-lg font-extrabold text-accent">
                  {(event.host_display_name ?? "P").slice(0, 1).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-lg font-extrabold text-foreground">
                    {event.host_display_name ?? "Pàdéyá host"}
                  </p>
                  <p className="text-sm text-muted-foreground">On Pàdéyá</p>
                </div>
              </div>
              {!previewMode ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {!isOwnHost && event.host_id ? (
                    <HostFollowControls
                      hostId={event.host_id}
                      hostSlug={event.host_slug || undefined}
                      hostDisplayName={event.host_display_name || "Host"}
                      loginNextPath={`/events/${event.slug}`}
                      size="md"
                    />
                  ) : null}
                  <Link
                    href={hostHref}
                    onClick={() =>
                      trackHostProfileClick({
                        targetEventId: event.id,
                        hostId: event.host_id,
                      })
                    }
                  >
                    <Button variant="secondary">View profile</Button>
                  </Link>
                  {event.host_id && !isOwnHost ? (
                    <StartMessageButton
                      hostId={event.host_id}
                      hostUsername={event.host_slug || undefined}
                      relatedEventId={event.id}
                      label="Message host"
                      variant="secondary"
                      returnPath={`/events/${event.slug}`}
                    />
                  ) : null}
                </div>
              ) : null}
              {(memory?.upcoming_events ?? []).length > 0 ? (
                <div className="mt-5 border-t border-border pt-4">
                  <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
                    More from {event.host_display_name || "this host"}
                  </p>
                  <ul className="mt-2 space-y-2">
                    {(memory?.upcoming_events ?? []).slice(0, 3).map((row) => (
                      <li key={row.id}>
                        <Link
                          href={`/events/${row.slug}`}
                          className="font-semibold text-foreground underline decoration-accent underline-offset-4"
                        >
                          {row.title} →
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>

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
              user ? (
                <EventDetailRecommendationsRail event={event} />
              ) : (
                <EventRelatedSections event={event} allEvents={related} />
              )
            ) : null}

            <CompletedEventDiscoveryCTA
              event={event}
              previewMode={previewMode}
              isOwnHost={isOwnHost}
            />
          </div>

          <CompletedEventSidebar
            event={event}
            memory={memory}
            previewMode={previewMode}
            isOwnHost={isOwnHost}
            manageEventHref={manageEventHref}
          />
        </div>
      </Container>

      {/* Mobile sticky: View memories only — never purchase CTAs */}
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur dark:bg-surface-elevated/95 lg:hidden">
        <Container className="flex items-center gap-3 !px-0">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold text-foreground">
              {event.title}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              Past event
              {memoryCount > 0 ? ` · ${memoryCount} memories` : ""}
            </p>
          </div>
          {previewMode ? (
            <Button className="shrink-0 whitespace-nowrap" disabled>
              Preview only
            </Button>
          ) : isOwnHost ? (
            <Link href={manageEventHref} className="shrink-0">
              <Button className="whitespace-nowrap">Manage</Button>
            </Link>
          ) : (
            <Link href={memoriesPath} className="shrink-0">
              <Button className="whitespace-nowrap">View memories</Button>
            </Link>
          )}
        </Container>
      </div>
    </main>
  );
}
