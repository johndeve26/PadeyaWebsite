import type { EventItem } from "@/lib/types/events";
import { formatPublicPlaceLabel, locationVisibilityOf } from "@/lib/event-privacy";

import type { SeoEnvInput } from "./env-policy";
import { absoluteUrl, buildPageMetadata, siteOrigin } from "./site";

/** Visibility values that must never be indexed when slug-reachable. */
const NOINDEX_VISIBILITIES = new Set([
  "unlisted",
  "password_protected",
]);

export function eventVisibilityOf(event: Pick<EventItem, "visibility">): string {
  return (event.visibility || "listed").trim().toLowerCase();
}

export function isEventSeoIndexable(
  event: Pick<EventItem, "visibility">,
): boolean {
  return !NOINDEX_VISIBILITIES.has(eventVisibilityOf(event));
}

export function isPasswordProtectedEvent(
  event: Pick<EventItem, "visibility">,
): boolean {
  return eventVisibilityOf(event) === "password_protected";
}

function publicLocationLabel(event: EventItem): string {
  return (
    formatPublicPlaceLabel(event) ||
    (locationVisibilityOf(event) === "online_only"
      ? "Online Event"
      : "Pàdéyá")
  );
}

function scrubPrivateAddress(
  text: string,
  event: EventItem,
  place: string,
): string {
  if (event.location_address_revealed === true) return text;
  const addr = event.address?.trim();
  if (!addr) return text;
  let next = text.includes(addr) ? text.replaceAll(addr, place) : text;
  // Scrub leading street fragment (e.g. "12 Admiralty Way, Lekki").
  if (addr.includes(",")) {
    const first = addr.split(",", 1)[0]?.trim();
    if (first && first.length >= 6 && next.includes(first)) {
      next = next.replaceAll(first, place);
    }
  }
  return next;
}

export function buildEventMetadata(event: EventItem, env?: SeoEnvInput) {
  const place = publicLocationLabel(event);
  const indexable = isEventSeoIndexable(event);
  const password = isPasswordProtectedEvent(event);

  // Password gate: never leak protected body copy into meta before unlock.
  if (password) {
    return buildPageMetadata({
      title: scrubPrivateAddress(event.title, event, place),
      description: `Password-protected event on Pàdéyá.`,
      path: `/events/${event.slug}`,
      // Prefer explicit social share art only; avoid treating body media as public.
      image: event.social_share_image_url || null,
      noIndex: true,
      env,
    });
  }

  const title = scrubPrivateAddress(
    event.seo_title || event.social_share_title || event.title,
    event,
    place,
  );
  const rawDescription =
    event.seo_description ||
    event.social_share_description ||
    event.short_tagline ||
    event.description.slice(0, 160);
  const description = scrubPrivateAddress(rawDescription, event, place);
  const image =
    event.social_share_image_url || event.banner_url || event.mobile_banner_url;

  return buildPageMetadata({
    title,
    description,
    path: `/events/${event.slug}`,
    image,
    noIndex: !indexable,
    env,
  });
}

/**
 * Map real event lifecycle `status` → schema.org EventStatusType URL.
 *
 * Platform notes (do not invent):
 * - Public detail API only returns `published` events today.
 * - There is no first-class `postponed` / `rescheduled` status
 *   (`postpone_event` only moves datetimes while status stays published).
 * - Past published events remain `EventScheduled` (not Cancelled).
 * - `cancelled` is mapped for completeness if a row is ever serialized;
 *   it is not currently served on public SEO pages (404).
 */
export function eventStatusSchemaUrl(
  event: Pick<EventItem, "status">,
): string | undefined {
  const s = (event.status || "").trim().toLowerCase();
  switch (s) {
    case "published":
    case "paused":
      return "https://schema.org/EventScheduled";
    case "cancelled":
      return "https://schema.org/EventCancelled";
    default:
      // draft / pending_review / completed / rejected / archived — do not guess
      return undefined;
  }
}

export function eventJsonLd(event: EventItem): Record<string, unknown> | null {
  // Do not emit rich Event schema for password-gated content.
  if (isPasswordProtectedEvent(event)) {
    return null;
  }

  const locationName = publicLocationLabel(event);
  const visibility = locationVisibilityOf(event);
  const showStreet =
    event.location_address_revealed === true && Boolean(event.address);
  const allowLocality =
    visibility === "full_public" ||
    visibility === "area_only" ||
    event.location_address_revealed === true;

  const place: Record<string, unknown> =
    visibility === "online_only" && !showStreet
      ? { "@type": "VirtualLocation", name: locationName }
      : { "@type": "Place", name: locationName };

  if (allowLocality && (event.city || event.state || showStreet)) {
    place.address = {
      "@type": "PostalAddress",
      addressLocality: event.city || undefined,
      addressRegion: event.state || undefined,
      streetAddress: showStreet ? event.address : undefined,
      addressCountry: event.country || "NG",
    };
  }

  // Exact geo only when address is revealed — never approximate pins in SEO.
  if (
    event.location_address_revealed === true &&
    event.latitude &&
    event.longitude
  ) {
    place.geo = {
      "@type": "GeoCoordinates",
      latitude: event.latitude,
      longitude: event.longitude,
    };
  }

  const offers = (event.ticket_types ?? [])
    .filter((t) => t.visibility !== "hidden" && t.status !== "inactive")
    .map((t) => ({
      "@type": "Offer",
      name: t.name,
      price: String(t.price),
      priceCurrency: "NGN",
      availability:
        (t.quantity ?? 0) - (t.quantity_sold ?? 0) > 0
          ? "https://schema.org/InStock"
          : "https://schema.org/SoldOut",
      // Checkout URL may appear in Offer; the checkout route itself is noindex.
      url: absoluteUrl(`/events/${event.slug}/checkout`),
    }));

  const jsonDescription = scrubPrivateAddress(
    event.short_tagline || event.description.slice(0, 300),
    event,
    locationName,
  );

  const url = absoluteUrl(`/events/${event.slug}`);
  const eventStatus = eventStatusSchemaUrl(event);

  const organizer = event.host_display_name
    ? (() => {
        const org: Record<string, unknown> = {
          "@type": "Organization",
          name: event.host_display_name,
        };
        if (event.host_slug?.trim()) {
          const hostUrl = absoluteUrl(
            `/u/${encodeURIComponent(event.host_slug.trim())}`,
          );
          org.url = hostUrl;
          org["@id"] = `${hostUrl}#organization`;
        }
        return org;
      })()
    : undefined;

  const json: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Event",
    "@id": `${url}#event`,
    name: event.title,
    description: jsonDescription,
    image: event.banner_url || undefined,
    startDate: event.start_datetime,
    endDate: event.end_datetime,
    eventAttendanceMode:
      event.event_type === "online"
        ? "https://schema.org/OnlineEventAttendanceMode"
        : event.event_type === "hybrid"
          ? "https://schema.org/MixedEventAttendanceMode"
          : "https://schema.org/OfflineEventAttendanceMode",
    location: place,
    organizer,
    offers: offers.length ? offers : undefined,
    url,
  };
  if (eventStatus) json.eventStatus = eventStatus;
  return json;
}

export { siteOrigin };
