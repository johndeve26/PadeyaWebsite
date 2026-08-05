/**
 * Pure helpers for public Event Open Graph copy + card fields.
 */

import { isFreeEvent } from "@/lib/discovery/event-filters";
import { ticketAvailabilityLabel } from "@/lib/discovery/marketplace-groups";
import {
  formatPublicPlaceLabel,
  locationVisibilityOf,
} from "@/lib/event-privacy";
import { formatDateTime } from "@/lib/format";
import { truncateEllipsis } from "@/lib/seo/host-og-presentation";
import type { EventItem, EventMedia } from "@/lib/types/events";

export const EVENT_OG_GOLD = "#D4AF37";
export const EVENT_OG_MUTED = "rgba(255,255,255,0.78)";
export const EVENT_OG_DIM = "rgba(255,255,255,0.55)";

export type EventOgLayoutVariant =
  | "standard"
  | "compact"
  | "long-title"
  | "flyer-side"
  | "full-background";

export type EventOgDateBlock = {
  month: string;
  day: string;
  weekday: string;
};

export type EventOgMediaPick = {
  url: string;
  source: "social" | "banner" | "mobile" | "gallery";
};

function publicTickets(event: EventItem) {
  return (event.ticket_types ?? []).filter(
    (t) => t.visibility !== "hidden" && t.status !== "inactive",
  );
}

export function eventOgCanonicalPath(slug: string): string {
  return `/events/${encodeURIComponent(slug.trim())}`;
}

export function eventOgImagePath(slug: string): string {
  return `${eventOgCanonicalPath(slug)}/opengraph-image`;
}

export function eventOgCategory(event: EventItem): string | null {
  const name = event.category?.name?.trim();
  return truncateEllipsis(name, 22) || null;
}

export function eventOgTagline(event: EventItem): string | null {
  const t = event.short_tagline?.trim();
  if (!t) return null;
  return truncateEllipsis(t, 72);
}

export function eventOgHostLine(event: EventItem): string | null {
  const name = event.host_display_name?.trim();
  if (!name) return null;
  return truncateEllipsis(`Hosted by ${name}`, 42);
}

export function eventOgLocation(event: EventItem): string | null {
  const place =
    formatPublicPlaceLabel(event) ||
    (locationVisibilityOf(event) === "online_only" ? "Online Event" : null);
  return place ? truncateEllipsis(place, 48) : null;
}

export function eventOgPrivacyNote(event: EventItem): string | null {
  const msg = event.location_privacy_message?.trim();
  if (msg) return truncateEllipsis(msg, 48);
  const vis = locationVisibilityOf(event);
  if (
    vis === "hidden_until_payment" ||
    vis === "area_only" ||
    vis === "hidden_until_24h_before"
  ) {
    if (vis === "hidden_until_24h_before") {
      return "Exact venue revealed 24 hours before";
    }
    return "Exact venue revealed after purchase";
  }
  return null;
}

export function eventOgWhenLine(event: EventItem): string {
  const tz = event.timezone?.trim() || "Africa/Lagos";
  return formatDateTime(event.start_datetime, tz);
}

export function eventOgDateBlock(event: EventItem): EventOgDateBlock | null {
  const raw = event.start_datetime;
  if (!raw) return null;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return null;
  const tz = event.timezone?.trim() || "Africa/Lagos";
  const fmt = new Intl.DateTimeFormat("en-GB", {
    timeZone: tz,
    month: "short",
    day: "numeric",
    weekday: "short",
  });
  const parts = fmt.formatToParts(d);
  const pick = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((p) => p.type === type)?.value ?? "";
  return {
    month: pick("month").toUpperCase(),
    day: pick("day"),
    weekday: pick("weekday").toUpperCase(),
  };
}

export function eventOgPriceLabel(event: EventItem): string | null {
  const soldOut = ticketAvailabilityLabel(event) === "Sold out";
  if (soldOut) return "Sold out";
  const types = publicTickets(event);
  if (!types.length) return null;
  if (isFreeEvent({ ...event, ticket_types: types })) return "Free";
  const prices = types
    .map((t) => Number(t.price))
    .filter((n) => Number.isFinite(n));
  if (!prices.length) return "See tickets";
  const min = Math.min(...prices);
  if (min <= 0) return "Free";
  // ASCII-safe for ImageResponse (Satori cannot load ₦ glyph fonts reliably).
  const amount = Number(min).toLocaleString("en-NG", {
    maximumFractionDigits: Number.isInteger(min) ? 0 : 2,
  });
  return `From NGN ${amount}`;
}

export function eventOgStatusBadge(event: EventItem): string | null {
  const status = (event.status || "").toLowerCase();
  if (status === "cancelled") return "CANCELLED";
  const avail = ticketAvailabilityLabel(event);
  if (avail === "Sold out") return "SOLD OUT";
  if (event.featured) return "FEATURED";
  return null;
}

/** Image priority: social → banner → mobile → gallery. Never host avatar. */
export function pickEventOgMedia(event: EventItem): EventOgMediaPick | null {
  const social =
    event.social_share_image_url?.trim() ||
    pickMediaByType(event.media, "social_share");
  if (social) return { url: social, source: "social" };

  const banner =
    event.banner_media?.og_url ||
    event.banner_media?.display_url ||
    event.banner_media?.url ||
    event.banner_url?.trim() ||
    null;
  if (banner) return { url: banner, source: "banner" };

  const mobile = event.mobile_banner_url?.trim();
  if (mobile) return { url: mobile, source: "mobile" };

  const gallery = pickMediaByType(event.media, "gallery");
  if (gallery) return { url: gallery, source: "gallery" };

  return null;
}

function pickMediaByType(
  media: EventMedia[] | undefined,
  type: string,
): string | null {
  const row = (media || []).find(
    (m) => m.media_type === type && (m.url || "").trim(),
  );
  return row?.url?.trim() || null;
}

export function eventOgPageTitle(event: EventItem): string {
  const title = event.seo_title?.trim() || event.title.trim() || "Event";
  const place = eventOgLocation(event);
  if (place && place !== "Pàdéyá" && place !== "Online Event") {
    return truncateEllipsis(`${title} in ${place} | Tickets on Pàdéyá`, 70);
  }
  return truncateEllipsis(`${title} | Tickets on Pàdéyá`, 70);
}

export function eventOgPageDescription(event: EventItem): string {
  const name = event.title.trim() || "this event";
  const raw =
    event.seo_description?.trim() ||
    event.social_share_description?.trim() ||
    event.short_tagline?.trim() ||
    "";
  if (raw.length >= 24) return truncateEllipsis(raw, 160);
  return truncateEllipsis(
    `Get tickets for ${name} on Pàdéyá. See the date, public location, ticket options and event details.`,
    160,
  );
}

export function selectEventOgLayout(opts: {
  density: "short" | "medium" | "long" | "very-long";
  hasFlyerSide: boolean;
  hasBackground: boolean;
}): EventOgLayoutVariant {
  if (opts.hasFlyerSide) return "flyer-side";
  if (opts.density === "very-long" || opts.density === "long") return "long-title";
  if (opts.hasBackground) return "full-background";
  if (opts.density === "short") return "standard";
  return "compact";
}

/** Classify aspect for flyer framing. */
export function classifyImageAspect(
  width: number,
  height: number,
): "landscape" | "portrait" | "square" {
  if (!width || !height) return "landscape";
  const r = width / height;
  if (r >= 1.45) return "landscape";
  if (r <= 0.85) return "portrait";
  return "square";
}
