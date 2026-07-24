import type { EventItem, LocationVisibility } from "@/lib/types/events";

const HIDDEN_VISIBILITIES = new Set<string>([
  "hidden_until_payment",
  "hidden_until_24h_before",
  "hidden_until_manual_approval",
]);

export function locationVisibilityOf(
  event: Pick<EventItem, "location_visibility">,
): LocationVisibility | string {
  return event.location_visibility || "full_public";
}

/**
 * Public-safe place line for cards, picks, and listings.
 *
 * - full_public: venue / public label / city-area (no private street when not revealed)
 * - area_only: area/city only — never street address
 * - hidden_*: public_location_label only
 * - online_only: "Online Event"
 *
 * Taxonomy country/state/city/area may still drive discovery filters; this helper
 * only controls what humans see on public surfaces.
 */
export function formatPublicPlaceLabel(
  event: Pick<
    EventItem,
    | "location_visibility"
    | "public_location_label"
    | "location_address_revealed"
    | "venue_name"
    | "address"
    | "city"
    | "state"
    | "location"
  >,
): string | null {
  const visibility = locationVisibilityOf(event);
  const label = event.public_location_label?.trim() || null;

  if (visibility === "online_only") {
    return label || "Online Event";
  }

  if (HIDDEN_VISIBILITIES.has(String(visibility))) {
    return label;
  }

  if (visibility === "area_only") {
    if (label) return label;
    const kind = event.location?.kind;
    if (kind === "area" || kind === "city") {
      return event.location?.name || null;
    }
    const parts = [event.city, event.state].filter(Boolean);
    return parts.length ? parts.join(", ") : null;
  }

  // full_public — still never put street address on cards
  const revealed = event.location_address_revealed !== false;
  if (!revealed) {
    return label;
  }
  if (label) return label;
  const parts = [event.venue_name, event.city || event.location?.name, event.state]
    .filter(Boolean)
    .map(String);
  const unique: string[] = [];
  for (const part of parts) {
    if (!unique.includes(part)) unique.push(part);
  }
  return unique.length ? unique.join(", ") : null;
}

/**
 * Detail / ticket place line.
 * Street address only when the API marks `location_address_revealed`
 * (host/admin always; buyers when payment/timing allows).
 */
export function formatPublicVenueDetail(
  event: Pick<
    EventItem,
    | "location_visibility"
    | "public_location_label"
    | "location_address_revealed"
    | "venue_name"
    | "address"
    | "city"
    | "state"
    | "location"
  >,
): string {
  const visibility = locationVisibilityOf(event);
  const revealed = event.location_address_revealed === true;

  if (revealed) {
    const parts = [event.venue_name, event.address, event.city, event.state].filter(
      Boolean,
    );
    return parts.length
      ? parts.join(", ")
      : formatPublicPlaceLabel(event) || "Location TBA";
  }

  if (visibility === "online_only") {
    return event.public_location_label?.trim() || "Online Event";
  }

  if (HIDDEN_VISIBILITIES.has(String(visibility))) {
    return (
      event.public_location_label?.trim() ||
      "Location details shared with ticket holders"
    );
  }

  if (visibility === "area_only") {
    return (
      formatPublicPlaceLabel(event) ||
      "Area shared — exact venue revealed later"
    );
  }

  return formatPublicPlaceLabel(event) || "Location TBA";
}

/** True when maps / street-level links are safe to show. */
export function canShowPublicMapsLink(
  event: Pick<
    EventItem,
    "location_visibility" | "location_address_revealed" | "address"
  >,
): boolean {
  return (
    event.location_address_revealed === true && Boolean(event.address?.trim())
  );
}

/** Whether the online join URL is safe to render for this payload. */
export function canShowOnlineEventUrl(
  event: Pick<EventItem, "online_event_url">,
): boolean {
  return Boolean(event.online_event_url?.trim());
}

/** Shape a host/admin event payload the way an anonymous guest would see it. */
export function asGuestPublicEvent(event: EventItem): EventItem {
  const visibility = locationVisibilityOf(event);
  const reveal = visibility === "full_public";
  const revealUrl =
    (event.online_url_reveal_rule || "after_payment") === "immediately";

  const label =
    formatPublicPlaceLabel({
      ...event,
      location_address_revealed: reveal,
    }) ||
    (HIDDEN_VISIBILITIES.has(String(visibility))
      ? "Location details shared with ticket holders"
      : null);

  const privacyMessage =
    event.reveal_note ||
    ({
      area_only: "Exact venue revealed after purchase.",
      hidden_until_payment: "Exact venue revealed after purchase.",
      hidden_until_24h_before: "Exact venue revealed 24 hours before the event.",
      hidden_until_manual_approval: "Full details sent to approved attendees.",
      online_only: "Online link revealed after payment.",
    } as Record<string, string>)[String(visibility)] ||
    null;

  const scrub = (value: string | null | undefined) => {
    if (!value || reveal || !event.address?.trim()) return value ?? null;
    const addr = event.address.trim();
    let next = value.includes(addr) ? value.replaceAll(addr, label || "secret location") : value;
    if (addr.includes(",")) {
      const first = addr.split(",", 1)[0]?.trim();
      if (first && first.length >= 6 && next.includes(first)) {
        next = next.replaceAll(first, label || "secret location");
      }
    }
    return next;
  };

  return {
    ...event,
    location_address_revealed: reveal,
    public_location_label: label,
    location_privacy_message: reveal ? null : privacyMessage,
    address: reveal ? event.address : null,
    venue_name:
      !reveal &&
      label &&
      visibility !== "area_only" &&
      visibility !== "full_public"
        ? label
        : event.venue_name,
    online_event_url: revealUrl ? event.online_event_url : null,
    seo_title: scrub(event.seo_title),
    seo_description: scrub(event.seo_description),
    social_share_title: scrub(event.social_share_title),
    social_share_description: scrub(event.social_share_description),
    description: scrub(event.description) || event.description,
  };
}
