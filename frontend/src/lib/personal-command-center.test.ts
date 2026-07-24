import { describe, expect, it } from "vitest";

import {
  buildActivityChips,
  hasAttentionSignals,
  isQuietPersonalHome,
  openRefundCount,
  passportVisibilityLabel,
  pickNextTicket,
  pickReviewPromptTicket,
  resolveNextUp,
  resolveCartCheckoutPath,
  safeTicketLocationLabel,
  shouldShowAmbassadorStrip,
  shouldShowCommunityStrip,
} from "./personal-command-center";
import type { Ticket } from "./types/commerce";
import type { RefundRequest } from "./types/finance";
import type { MerchFulfillment } from "./types/merch";
import type { AmbassadorEarningsSummary } from "./types/promos";

function ticket(partial: Partial<Ticket> & Pick<Ticket, "id">): Ticket {
  return {
    public_code: "T-1",
    event_id: "e1",
    order_id: "o1",
    ticket_type_id: "tt1",
    ticket_type_name: "GA",
    status: "active",
    holder_name: "Ada",
    holder_email: "ada@example.com",
    created_at: "2026-07-01T00:00:00Z",
    event_title: "Night Out",
    event_starts_at: "2099-08-01T20:00:00Z",
    ...partial,
  };
}

describe("personal-command-center helpers", () => {
  it("picks the soonest upcoming active ticket", () => {
    const next = pickNextTicket([
      ticket({
        id: "later",
        event_starts_at: "2099-09-01T20:00:00Z",
      }),
      ticket({
        id: "sooner",
        event_starts_at: "2099-08-01T20:00:00Z",
      }),
    ]);
    expect(next?.id).toBe("sooner");
  });

  it("never picks cancelled, refunded, or invalid tickets as next up", () => {
    expect(
      pickNextTicket([
        ticket({ id: "c", status: "cancelled" }),
        ticket({ id: "r", status: "refunded" }),
        ticket({ id: "i", status: "invalid" }),
        ticket({ id: "ok" }),
      ])?.id,
    ).toBe("ok");
    expect(
      pickNextTicket([ticket({ id: "pending", status: "pending" })]),
    ).toBeNull();
  });

  it("uses only API location_label for safe place text", () => {
    expect(safeTicketLocationLabel({ location_label: "  Lekki  " })).toBe(
      "Lekki",
    );
    expect(safeTicketLocationLabel({ location_label: null })).toBeNull();
  });

  it("resolves next-up priority ticket > merch > cart > empty", () => {
    const ready = {
      id: "m1",
      order_item_id: "oi1",
      display_status: "ready_for_pickup",
      status: "ready_for_pickup",
      product_name_snapshot: "Tee",
    } as MerchFulfillment;

    expect(
      resolveNextUp({
        tickets: [ticket({ id: "t1" })],
        merch: [ready],
        cart: { items: [{ quantity: 2 }], resume_path: "/dashboard/cart" },
      }).primary.kind,
    ).toBe("ticket");

    expect(
      resolveNextUp({
        tickets: [ticket({ id: "bad", status: "refunded" })],
        merch: [ready],
        cart: { items: [{ quantity: 1 }], resume_path: "/dashboard/cart" },
      }).primary.kind,
    ).toBe("merch");

    expect(
      resolveNextUp({
        tickets: [],
        merch: [],
        cart: { items: [{ quantity: 1 }], resume_path: "/dashboard/cart" },
      }).primary,
    ).toEqual({
      kind: "cart",
      cartLines: 1,
      resumePath: "/dashboard/cart",
    });

    expect(
      resolveNextUp({
        tickets: [],
        merch: [],
        cart: {
          items: [{ quantity: 1 }],
          resume_path: "/dashboard/cart",
          event_slug: "summer-night",
        },
      }).primary,
    ).toEqual({
      kind: "cart",
      cartLines: 1,
      resumePath: "/events/summer-night/checkout",
    });

    expect(
      resolveNextUp({
        tickets: [],
        merch: [],
        cart: {
          items: [{ quantity: 1 }],
          resume_path: "/dashboard/cart",
          host_slug: "dj-maze",
        },
      }).primary,
    ).toEqual({
      kind: "cart",
      cartLines: 1,
      resumePath: "/merch/hosts/dj-maze/checkout",
    });

    expect(
      resolveNextUp({ tickets: [], merch: [], cart: null }).primary.kind,
    ).toBe("empty");
  });

  it("resolves cart checkout path from event slug", () => {
    expect(
      resolveCartCheckoutPath({
        resume_path: "/dashboard/cart",
        event_slug: "afrobeats-live",
      }),
    ).toBe("/events/afrobeats-live/checkout");
    expect(
      resolveCartCheckoutPath({
        resume_path: "/dashboard/cart",
        host_slug: "dj-maze",
      }),
    ).toBe("/merch/hosts/dj-maze/checkout");
    expect(
      resolveCartCheckoutPath({
        resume_path: "/events/x/checkout",
      }),
    ).toBe("/events/x/checkout");
    expect(resolveCartCheckoutPath(null)).toBeNull();
  });

  it("hides closed refunds from open count", () => {
    const rows = [
      { status: "pending" },
      { status: "approved" },
      { status: "reviewing" },
    ] as RefundRequest[];
    expect(openRefundCount(rows)).toBe(2);
  });

  it("labels passport visibility in plain language", () => {
    expect(passportVisibilityLabel("private")).toBe("Private Passport");
    expect(passportVisibilityLabel("public")).toBe("Public on /fans");
  });

  it("shows ambassador strip only with activity signal", () => {
    expect(
      shouldShowAmbassadorStrip({
        enrollments_active: 0,
        payable_earnings: 0,
        estimated_earnings: 0,
      } as AmbassadorEarningsSummary),
    ).toBe(false);
    expect(
      shouldShowAmbassadorStrip({
        enrollments_active: 1,
        payable_earnings: 0,
        estimated_earnings: 0,
      } as AmbassadorEarningsSummary),
    ).toBe(true);
  });

  it("builds attention-focused activity chips including refunds", () => {
    const chips = buildActivityChips({
      tickets: [ticket({ id: "t1" }), ticket({ id: "t2", event_id: "e2" })],
      orders: [],
      merch: [],
      refunds: [],
      cartLines: 0,
    });
    expect(chips.map((c) => c.key)).toEqual([
      "tickets",
      "orders",
      "merch",
      "refunds",
    ]);
    expect(chips.find((c) => c.key === "tickets")?.value).toBe(
      "2 ready for entry",
    );
    expect(chips.find((c) => c.key === "orders")?.value).toBe("0 pending orders");
    expect(chips.find((c) => c.key === "merch")?.value).toBe("0 pickups ready");
    expect(chips.find((c) => c.key === "refunds")?.value).toBe("0 open refunds");
  });

  it("picks a checked-in past ticket for review prompt", () => {
    const candidate = pickReviewPromptTicket(
      [
        ticket({
          id: "past",
          status: "checked_in",
          checked_in_at: "2026-01-01T22:00:00Z",
          event_starts_at: "2026-01-01T18:00:00Z",
          event_ends_at: "2026-01-01T23:00:00Z",
          event_status: "completed",
        }),
        ticket({ id: "future" }),
      ],
      [],
    );
    expect(candidate?.id).toBe("past");
  });

  it("skips tickets for owned host workspaces", () => {
    const candidate = pickReviewPromptTicket(
      [
        ticket({
          id: "own-host",
          status: "checked_in",
          checked_in_at: "2026-01-02T22:00:00Z",
          event_starts_at: "2026-01-02T18:00:00Z",
          event_ends_at: "2026-01-02T23:00:00Z",
          event_status: "completed",
          host_id: "host-a",
        }),
        ticket({
          id: "other-host",
          status: "checked_in",
          checked_in_at: "2026-01-01T22:00:00Z",
          event_starts_at: "2026-01-01T18:00:00Z",
          event_ends_at: "2026-01-01T23:00:00Z",
          event_status: "completed",
          host_id: "host-b",
        }),
      ],
      [],
      new Date("2026-02-01T00:00:00Z"),
      { excludeHostIds: ["host-a"] },
    );
    expect(candidate?.id).toBe("other-host");
  });

  it("skips tickets already reviewed", () => {
    const candidate = pickReviewPromptTicket(
      [
        ticket({
          id: "past",
          status: "checked_in",
          checked_in_at: "2026-01-01T22:00:00Z",
          event_starts_at: "2026-01-01T18:00:00Z",
          event_ends_at: "2026-01-01T23:00:00Z",
          event_status: "completed",
        }),
      ],
      [{ ticket_id: "past", event_id: "e1", status: "published" }],
    );
    expect(candidate).toBeNull();
  });

  it("detects quiet new-user home vs attention signals", () => {
    expect(
      isQuietPersonalHome({
        tickets: [],
        orders: [],
        merch: [],
        cart: null,
      }),
    ).toBe(true);
    expect(
      isQuietPersonalHome({
        tickets: [ticket({ id: "t1" })],
        orders: [],
        merch: [],
        cart: null,
      }),
    ).toBe(false);
    expect(
      hasAttentionSignals({
        tickets: [],
        orders: [],
        merch: [],
        refunds: [],
        cartLines: 0,
      }),
    ).toBe(false);
    expect(
      hasAttentionSignals({
        tickets: [ticket({ id: "t1" })],
        orders: [],
        merch: [],
        refunds: [],
        cartLines: 0,
      }),
    ).toBe(true);
    expect(
      shouldShowCommunityStrip({
        unreadMessages: 0,
        connectPending: 0,
        followingCount: 0,
      }),
    ).toBe(false);
    expect(
      shouldShowCommunityStrip({
        unreadMessages: 1,
        connectPending: 0,
        followingCount: 0,
      }),
    ).toBe(true);
  });
});
