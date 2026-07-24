import type { EventItem, Host } from "@/lib/types/events";
import type { LegacyPage } from "@/lib/types/legacy";

export type RoadmapStatus = "not_started" | "in_progress" | "done" | "skipped";

export type RoadmapCategory = "launch" | "grow" | "operate";

export type RoadmapItem = {
  id: string;
  label: string;
  why: string;
  href: string;
  status: RoadmapStatus;
  category: RoadmapCategory;
  sortOrder: number;
};

export type RoadmapContext = {
  host: Host | null;
  legacy: LegacyPage | null;
  events: EventItem[];
  teamMemberCount: number;
  merchProductCount: number;
  campaignCount: number;
  sponsorshipSlotCount: number;
};

function firstEvent(events: EventItem[]): EventItem | null {
  if (events.length === 0) return null;
  return (
    events.find((e) => e.status === "published") ??
    events.find((e) => e.status === "draft") ??
    events[0] ??
    null
  );
}

function legacyLooksComplete(legacy: LegacyPage | null): boolean {
  if (!legacy) return false;
  const profile = legacy.profile;
  const hasIdentity = Boolean(
    profile?.bio?.trim() &&
      profile.avatar_url &&
      (legacy.tagline?.trim() || legacy.about?.trim()),
  );
  const visibleBlocks =
    legacy.content_blocks?.filter((block) => block.is_visible).length ?? 0;
  return hasIdentity && visibleBlocks >= 1;
}

function eventWithTickets(events: EventItem[]): EventItem | null {
  return (
    events.find((e) => (e.ticket_types?.length ?? 0) > 0) ??
    firstEvent(events)
  );
}

function publishedEvent(events: EventItem[]): EventItem | null {
  return events.find((e) => e.status === "published") ?? null;
}

function eventHasMedia(event: EventItem | null): boolean {
  if (!event) return false;
  if (event.publish_checklist?.banner_ready) return true;
  if (event.banner_url?.trim()) return true;
  return (event.media ?? []).some(
    (item) =>
      item.media_type === "banner" ||
      item.media_type === "gallery" ||
      item.media_type === "mobile_banner",
  );
}

export function roadmapCtaLabel(status: RoadmapStatus): string {
  switch (status) {
    case "done":
      return "Review";
    case "in_progress":
      return "Continue";
    case "skipped":
      return "Skipped";
    default:
      return "Start";
  }
}

export function roadmapStatusLabel(status: RoadmapStatus): string {
  switch (status) {
    case "done":
      return "Done";
    case "in_progress":
      return "In progress";
    case "skipped":
      return "Skipped";
    default:
      return "Not started";
  }
}

export function buildRoadmapItems(ctx: RoadmapContext): RoadmapItem[] {
  const { host, legacy, events } = ctx;
  const profile = host?.profile ?? legacy?.profile ?? null;
  const taxonomy = host?.taxonomy;
  const draftOrLive = firstEvent(events);
  const ticketEvent = eventWithTickets(events);
  const live = publishedEvent(events);

  const items: Omit<RoadmapItem, "status">[] = [
    {
      id: "host-profile",
      label: "Complete host profile",
      why: "Fans trust a complete identity on your Legacy Page.",
      href: "/host/settings",
      category: "launch",
      sortOrder: 10,
    },
    {
      id: "host-media",
      label: "Add logo/avatar and cover",
      why: "Visual credibility on your public Legacy Page.",
      href: "/host/legacy/edit",
      category: "launch",
      sortOrder: 20,
    },
    {
      id: "host-taxonomy",
      label: "Set category and location",
      why: "Discovery and SEO for your nights.",
      href: "/host/settings",
      category: "launch",
      sortOrder: 30,
    },
    {
      id: "legacy-page",
      label: "Complete Legacy Page",
      why: "Your permanent public reputation surface.",
      href: "/host/legacy",
      category: "launch",
      sortOrder: 40,
    },
    {
      id: "first-event",
      label: "Create first event",
      why: "Core revenue path on Pàdéyá.",
      href: "/host/events/new",
      category: "launch",
      sortOrder: 50,
    },
    {
      id: "ticket-types",
      label: "Add ticket types",
      why: "You cannot sell without tiers.",
      href: ticketEvent
        ? `/host/events/${ticketEvent.id}/tickets`
        : "/host/events/new",
      category: "launch",
      sortOrder: 60,
    },
    {
      id: "event-location",
      label: "Set location/privacy",
      why: "Trust and compliance for attendees.",
      href: draftOrLive
        ? `/host/events/${draftOrLive.id}/edit?step=location`
        : "/host/events/new",
      category: "launch",
      sortOrder: 70,
    },
    {
      id: "event-media",
      label: "Add event media",
      why: "Banner and visuals sell the night before checkout.",
      href: draftOrLive
        ? `/host/events/${draftOrLive.id}/edit?step=media`
        : "/host/events/new",
      category: "launch",
      sortOrder: 75,
    },
    {
      id: "publish-event",
      label: "Publish event",
      why: "Go live on Pàdéyá discovery.",
      href: draftOrLive
        ? `/host/events/${draftOrLive.id}/edit?step=publish`
        : "/host/events/new",
      category: "launch",
      sortOrder: 80,
    },
    {
      id: "test-checkout",
      label: "Test checkout",
      why: "Avoid launch-night payment surprises.",
      href: draftOrLive
        ? `/host/events/${draftOrLive.id}/preview`
        : "/host/events/new",
      category: "launch",
      sortOrder: 90,
    },
    {
      id: "invite-team",
      label: "Invite scanner/team staff",
      why: "Door ops without sharing your login.",
      href: "/host/team/invites",
      category: "operate",
      sortOrder: 100,
    },
    {
      id: "add-merch",
      label: "Add merch",
      why: "Incremental revenue at the door.",
      href: "/host/merchandise/new",
      category: "grow",
      sortOrder: 110,
    },
    {
      id: "enable-ambassadors",
      label: "Enable ambassadors",
      why: "Growth loop from fan referrals.",
      href: "/host/ambassadors/campaigns/new",
      category: "grow",
      sortOrder: 120,
    },
    {
      id: "sponsorship-slots",
      label: "Add sponsorship slots",
      why: "Brand partnerships on your nights.",
      href: "/host/sponsorships/new",
      category: "grow",
      sortOrder: 130,
    },
    {
      id: "share-event",
      label: "Share event",
      why: "Drive ticket sales from your audience.",
      href: live?.slug ? `/events/${live.slug}` : "/host/events",
      category: "grow",
      sortOrder: 140,
    },
    {
      id: "review-analytics",
      label: "Review analytics",
      why: "Close the feedback loop after launch.",
      href: "/host/analytics",
      category: "operate",
      sortOrder: 150,
    },
  ];

  return items
    .map((item) => ({
      ...item,
      status: inferRoadmapStatus(item.id, ctx, {
        profile,
        taxonomy,
        draftOrLive,
        ticketEvent,
        live,
      }),
    }))
    .sort((a, b) => a.sortOrder - b.sortOrder);
}

function inferRoadmapStatus(
  id: string,
  ctx: RoadmapContext,
  helpers: {
    profile: Host["profile"];
    taxonomy: Host["taxonomy"];
    draftOrLive: EventItem | null;
    ticketEvent: EventItem | null;
    live: EventItem | null;
  },
): RoadmapStatus {
  const { profile, taxonomy, draftOrLive, ticketEvent, live } = helpers;

  switch (id) {
    case "host-profile":
      if (profile?.bio?.trim() && ctx.host?.display_name?.trim()) return "done";
      if (profile?.bio?.trim() || ctx.host?.display_name?.trim()) {
        return "in_progress";
      }
      return "not_started";
    case "host-media":
      if (profile?.avatar_url && profile.cover_url) return "done";
      if (profile?.avatar_url || profile?.cover_url) return "in_progress";
      return "not_started";
    case "host-taxonomy":
      if (
        taxonomy?.category_slugs?.length &&
        (taxonomy.primary_city_slug || profile?.city)
      ) {
        return "done";
      }
      if (taxonomy?.category_slugs?.length || profile?.city) {
        return "in_progress";
      }
      return "not_started";
    case "legacy-page":
      return legacyLooksComplete(ctx.legacy) ? "done" : "not_started";
    case "first-event":
      return ctx.events.length > 0 ? "done" : "not_started";
    case "ticket-types":
      if ((ticketEvent?.ticket_types?.length ?? 0) > 0) return "done";
      return ctx.events.length > 0 ? "in_progress" : "not_started";
    case "event-location":
      if (draftOrLive?.publish_checklist?.venue_privacy_complete) return "done";
      if (
        draftOrLive?.location_visibility &&
        draftOrLive.visibility
      ) {
        return "done";
      }
      return draftOrLive ? "in_progress" : "not_started";
    case "event-media":
      if (eventHasMedia(draftOrLive)) return "done";
      return draftOrLive ? "in_progress" : "not_started";
    case "publish-event":
      return live ? "done" : draftOrLive ? "in_progress" : "not_started";
    case "test-checkout":
      if (draftOrLive?.publish_checklist?.preview_checked) return "done";
      return live || draftOrLive ? "in_progress" : "not_started";
    case "invite-team":
      return ctx.teamMemberCount > 0 ? "done" : "not_started";
    case "add-merch":
      return ctx.merchProductCount > 0 ? "done" : "not_started";
    case "enable-ambassadors":
      if (ctx.campaignCount > 0) return "done";
      if (ctx.events.some((e) => e.open_ambassadors_enabled)) {
        return "in_progress";
      }
      return "not_started";
    case "sponsorship-slots":
      return ctx.sponsorshipSlotCount > 0 ? "done" : "not_started";
    case "share-event":
      return live?.slug ? "in_progress" : "not_started";
    case "review-analytics":
      return live ? "in_progress" : "not_started";
    default:
      return "not_started";
  }
}

export function incompleteRoadmapItems(
  items: RoadmapItem[],
  limit = 3,
): RoadmapItem[] {
  return items
    .filter((item) => item.status === "not_started" || item.status === "in_progress")
    .slice(0, limit);
}

export function nextBestRoadmapItem(items: RoadmapItem[]): RoadmapItem | null {
  return (
    items.find((item) => item.status === "in_progress") ??
    items.find((item) => item.status === "not_started") ??
    null
  );
}

export function roadmapProgress(items: RoadmapItem[]): {
  done: number;
  total: number;
} {
  const actionable = items.filter((item) => item.status !== "skipped");
  const done = actionable.filter((item) => item.status === "done").length;
  return { done, total: actionable.length };
}

export function filterRoadmapForDeskStaff(items: RoadmapItem[]): RoadmapItem[] {
  return items.filter((item) => item.category !== "grow");
}
