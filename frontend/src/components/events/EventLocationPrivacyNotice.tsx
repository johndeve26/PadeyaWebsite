import {
  canShowOnlineEventUrl,
  locationVisibilityOf,
} from "@/lib/event-privacy";
import type { EventItem } from "@/lib/types/events";

/**
 * Prominent notice when street address or online join link is withheld.
 * Relies on API scrubbing — never invents a private address.
 */
export function EventLocationPrivacyNotice({ event }: { event: EventItem }) {
  const visibility = locationVisibilityOf(event);
  const addressHidden = event.location_address_revealed !== true;
  const onlineRelevant =
    visibility === "online_only" ||
    event.event_type === "online" ||
    event.event_type === "hybrid";
  const onlineHidden = onlineRelevant && !canShowOnlineEventUrl(event);

  if (!addressHidden && !onlineHidden) return null;

  const message =
    event.location_privacy_message?.trim() ||
    (visibility === "online_only" || onlineHidden
      ? "Online link is revealed when your ticket allows it."
      : visibility === "area_only"
        ? "Exact venue is shared with ticket holders later."
        : "Exact venue is hidden until purchase or approval.");

  return (
    <aside
      className="rounded-[var(--radius-lg)] border border-primary/30 bg-[color-mix(in_srgb,var(--primary)_10%,var(--surface-elevated))] px-4 py-3.5 sm:px-5"
      aria-label="Location privacy"
    >
      <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
        Location privacy
      </p>
      <p className="mt-1 text-sm font-semibold leading-relaxed text-heading">
        {message}
      </p>
      {addressHidden && visibility !== "online_only" ? (
        <p className="mt-1 text-xs leading-relaxed text-body">
          Street address stays private on this page. Maps and directions appear
          only after the venue is revealed.
        </p>
      ) : null}
      {onlineHidden ? (
        <p className="mt-1 text-xs leading-relaxed text-body">
          The join link is not shown until your reveal rule allows it.
        </p>
      ) : null}
    </aside>
  );
}
