/**
 * Completed-event product helpers — keep purchase gates testable and shared.
 */

import { formatNgn } from "@/lib/format";
import type { EventItem, EventStatus } from "@/lib/types/events";

/** Canonical product gate: only backend `completed` status uses the archive layout. */
export function isCompletedEventStatus(status: EventStatus | string): boolean {
  return status === "completed";
}

/** Live / in-progress published events must not use the completed layout. */
export function isLiveOrUpcomingPurchaseStatus(
  status: EventStatus | string,
): boolean {
  return status === "published" || status === "paused";
}

export function canShowBuyTickets(opts: {
  status: EventStatus | string;
  previewMode?: boolean;
  hasTickets: boolean;
  anyTicketOpen: boolean;
}): boolean {
  if (opts.previewMode) return false;
  if (isCompletedEventStatus(opts.status)) return false;
  if (!isLiveOrUpcomingPurchaseStatus(opts.status)) return false;
  return opts.hasTickets && opts.anyTicketOpen;
}

export function historicalTicketsWereLabel(
  prices: Array<string | number | null | undefined>,
): string | null {
  const nums = prices
    .map((p) => Number(p))
    .filter((n) => Number.isFinite(n));
  if (!nums.length) return null;
  const min = Math.min(...nums);
  if (min === 0) return "Tickets were free";
  return `Tickets were from ${formatNgn(min)}`;
}

export function memoriesHref(slug: string): string {
  return `/events/${encodeURIComponent(slug)}/memories`;
}

export function cityEventsHref(city: string | null | undefined): string | null {
  if (!city?.trim()) return null;
  const citySlug = city
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return citySlug ? `/events/city/${citySlug}` : null;
}

export function pickMemoryPreviewPhotos<T extends { is_cover?: boolean }>(
  photos: T[],
  limit = 3,
): T[] {
  if (!photos.length) return [];
  const coverIdx = photos.findIndex((p) => p.is_cover);
  if (coverIdx <= 0) return photos.slice(0, limit);
  const cover = photos[coverIdx];
  const rest = photos.filter((_, i) => i !== coverIdx);
  return [cover, ...rest].slice(0, limit);
}

export function completedEventMetaLine(event: EventItem): string {
  const parts: string[] = [];
  if (event.short_tagline?.trim()) parts.push(event.short_tagline.trim());
  else if (event.vibe?.trim()) parts.push(event.vibe.trim());
  else if (event.category?.name) parts.push(event.category.name);
  return parts.join(" · ");
}
