import type { EventItem } from "@/lib/types/events";
import { formatPublicPlaceLabel, locationVisibilityOf } from "@/lib/event-privacy";

import { absoluteUrl, buildPageMetadata, siteOrigin } from "./site";

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

export function buildEventMetadata(event: EventItem) {
  const place = publicLocationLabel(event);
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
  // Never rely on private street address in public meta fallbacks.
  const description = scrubPrivateAddress(rawDescription, event, place);
  const image =
    event.social_share_image_url || event.banner_url || event.mobile_banner_url;
  return buildPageMetadata({
    title,
    description,
    path: `/events/${event.slug}`,
    image,
  });
}

export function eventJsonLd(event: EventItem): Record<string, unknown> {
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
      url: absoluteUrl(`/events/${event.slug}/checkout`),
    }));

  const jsonDescription = scrubPrivateAddress(
    event.short_tagline || event.description.slice(0, 300),
    event,
    locationName,
  );

  return {
    "@context": "https://schema.org",
    "@type": "Event",
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
    organizer: event.host_display_name
      ? {
          "@type": "Organization",
          name: event.host_display_name,
        }
      : undefined,
    offers: offers.length ? offers : undefined,
    url: absoluteUrl(`/events/${event.slug}`),
  };
}

export { siteOrigin };
