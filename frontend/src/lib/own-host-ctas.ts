/**
 * Own-host vs visitor CTA decisions for Pàdéyá public host/event pages.
 * Owner-only — team/staff are treated as visitors for these CTAs.
 */

export type HostPageCtaMode = "own_host" | "visitor";
export type EventPageCtaMode = "own_event" | "visitor";

export function hostPageCtaMode(isOwnHostOwner: boolean): HostPageCtaMode {
  return isOwnHostOwner ? "own_host" : "visitor";
}

export function eventPageCtaMode(isOwnHostOwner: boolean): EventPageCtaMode {
  return isOwnHostOwner ? "own_event" : "visitor";
}

export function hostPageCtas(mode: HostPageCtaMode) {
  if (mode === "own_host") {
    return {
      banner: "This is your host page" as const,
      primary: { label: "Open Host workspace" as const, href: "/host" },
      showFollow: false,
      showMessage: false,
      showConnect: false,
    };
  }
  return {
    banner: null,
    primary: null,
    showFollow: true,
    showMessage: true,
    showConnect: true,
  };
}

export function eventPageCtas(mode: EventPageCtaMode, eventId: string) {
  if (mode === "own_event") {
    return {
      primary: {
        label: "Manage event" as const,
        href: `/host/events/${eventId}`,
      },
      showBuyTicket: false,
      showBuyMerchCheckout: false,
    };
  }
  return {
    primary: { label: "Get tickets" as const, href: null as string | null },
    showBuyTicket: true,
    showBuyMerchCheckout: true,
  };
}

/** Host users keep Personal /dashboard — own-host CTA mode never blocks it. */
export function personalDashboardAllowed(isOwnHostOwner?: boolean): boolean {
  void isOwnHostOwner;
  return true;
}
