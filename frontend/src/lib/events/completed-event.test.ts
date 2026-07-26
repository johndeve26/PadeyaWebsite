import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import {
  canShowBuyTickets,
  cityEventsHref,
  historicalTicketsWereLabel,
  isCompletedEventStatus,
  isLiveOrUpcomingPurchaseStatus,
  memoriesHref,
  pickMemoryPreviewPhotos,
} from "@/lib/events/completed-event";

describe("completed event layout gates", () => {
  it("activates only for backend completed status", () => {
    expect(isCompletedEventStatus("completed")).toBe(true);
    expect(isCompletedEventStatus("published")).toBe(false);
    expect(isCompletedEventStatus("paused")).toBe(false);
  });

  it("does not treat live/upcoming as completed", () => {
    expect(isLiveOrUpcomingPurchaseStatus("published")).toBe(true);
    expect(isLiveOrUpcomingPurchaseStatus("paused")).toBe(true);
    expect(isLiveOrUpcomingPurchaseStatus("completed")).toBe(false);
  });

  it("hides Buy Ticket / checkout for completed events", () => {
    expect(
      canShowBuyTickets({
        status: "completed",
        hasTickets: true,
        anyTicketOpen: true,
      }),
    ).toBe(false);
  });

  it("keeps Buy Ticket for upcoming when tickets are open", () => {
    expect(
      canShowBuyTickets({
        status: "published",
        hasTickets: true,
        anyTicketOpen: true,
      }),
    ).toBe(true);
  });

  it("does not invent purchase UI for closed upcoming tickets", () => {
    expect(
      canShowBuyTickets({
        status: "published",
        hasTickets: true,
        anyTicketOpen: false,
      }),
    ).toBe(false);
  });

  it("formats historical pricing wording", () => {
    expect(historicalTicketsWereLabel([3500, 25000])).toBe(
      "Tickets were from ₦3,500",
    );
    expect(historicalTicketsWereLabel([0, 7000])).toBe("Tickets were free");
    expect(historicalTicketsWereLabel([])).toBeNull();
  });

  it("builds memories and city discovery hrefs", () => {
    expect(memoriesHref("demo-food-and-flow")).toBe(
      "/events/demo-food-and-flow/memories",
    );
    expect(cityEventsHref("Lagos")).toBe("/events/city/lagos");
  });

  it("prefers cover photo first in collage picks", () => {
    const photos = [
      { id: "a", is_cover: false },
      { id: "b", is_cover: true },
      { id: "c", is_cover: false },
    ];
    expect(pickMemoryPreviewPhotos(photos, 3).map((p) => p.id)).toEqual([
      "b",
      "a",
      "c",
    ]);
  });
});

describe("completed event source contracts", () => {
  const completedSrc = readFileSync(
    path.join(
      process.cwd(),
      "src/components/events/completed/CompletedEventPublicView.tsx",
    ),
    "utf8",
  );
  const sidebarSrc = readFileSync(
    path.join(
      process.cwd(),
      "src/components/events/completed/CompletedEventSidebar.tsx",
    ),
    "utf8",
  );
  const upcomingSrc = readFileSync(
    path.join(process.cwd(), "src/components/events/EventPublicView.tsx"),
    "utf8",
  );
  const ticketHistorySrc = readFileSync(
    path.join(
      process.cwd(),
      "src/components/events/completed/CompletedEventTicketHistory.tsx",
    ),
    "utf8",
  );

  it("routes completed events into the dedicated layout", () => {
    expect(upcomingSrc).toMatch(/CompletedEventPublicView/);
    expect(upcomingSrc).toMatch(/status === ["']completed["']/);
  });

  it("completed layout shows Past Event and View memories", () => {
    expect(completedSrc).toMatch(/Past event/);
    expect(completedSrc).toMatch(/View memories/);
    expect(sidebarSrc).toMatch(/Event ended/);
    expect(sidebarSrc).toMatch(/View memories/);
  });

  it("completed layout has no purchase or checkout CTAs", () => {
    expect(completedSrc).not.toMatch(/>\s*Get tickets\s*</);
    expect(completedSrc).not.toMatch(/>\s*Buy tickets?\s*</i);
    expect(completedSrc).not.toMatch(/href=\{[^}]*checkout/);
    expect(sidebarSrc).not.toMatch(/>\s*Get tickets\s*</);
    expect(sidebarSrc).not.toMatch(/href=\{[^}]*checkout/);
    expect(ticketHistorySrc).not.toMatch(/>\s*Get tickets\s*</);
    expect(ticketHistorySrc).not.toMatch(/min_per_order|max_per_order|quantity_sold/);
    expect(ticketHistorySrc).toMatch(/Original ticket options/);
  });

  it("upcoming layout still exposes Get tickets purchase path", () => {
    expect(upcomingSrc).toMatch(/Get tickets/);
    expect(upcomingSrc).toMatch(/checkoutHref/);
    expect(upcomingSrc).toMatch(/EventGallery/);
  });

  it("includes memories preview and discovery CTA", () => {
    expect(completedSrc).toMatch(/CompletedEventMemoriesPreview/);
    expect(completedSrc).toMatch(/CompletedEventDiscoveryCTA/);
  });
});
