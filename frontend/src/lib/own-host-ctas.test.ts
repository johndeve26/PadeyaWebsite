import { describe, expect, it } from "vitest";

import {
  eventPageCtaMode,
  eventPageCtas,
  hostPageCtaMode,
  hostPageCtas,
  personalDashboardAllowed,
} from "./own-host-ctas";

describe("own-host public CTAs", () => {
  it("own host page hides Follow/Message/Connect and shows Open Host workspace", () => {
    const mode = hostPageCtaMode(true);
    const ctas = hostPageCtas(mode);
    expect(mode).toBe("own_host");
    expect(ctas.banner).toBe("This is your host page");
    expect(ctas.primary).toEqual({
      label: "Open Host workspace",
      href: "/host",
    });
    expect(ctas.showFollow).toBe(false);
    expect(ctas.showMessage).toBe(false);
    expect(ctas.showConnect).toBe(false);
  });

  it("other host profile still shows Follow/Message", () => {
    const ctas = hostPageCtas(hostPageCtaMode(false));
    expect(ctas.showFollow).toBe(true);
    expect(ctas.showMessage).toBe(true);
    expect(ctas.showConnect).toBe(true);
    expect(ctas.primary).toBeNull();
    expect(ctas.banner).toBeNull();
  });

  it("own event page hides Buy ticket and shows Manage event", () => {
    const mode = eventPageCtaMode(true);
    const ctas = eventPageCtas(mode, "evt-123");
    expect(mode).toBe("own_event");
    expect(ctas.showBuyTicket).toBe(false);
    expect(ctas.showBuyMerchCheckout).toBe(false);
    expect(ctas.primary).toEqual({
      label: "Manage event",
      href: "/host/events/evt-123",
    });
  });

  it("other host event still shows Buy ticket", () => {
    const ctas = eventPageCtas(eventPageCtaMode(false), "evt-456");
    expect(ctas.showBuyTicket).toBe(true);
    expect(ctas.showBuyMerchCheckout).toBe(true);
    expect(ctas.primary?.label).toBe("Get tickets");
  });

  it("host user can still access /dashboard", () => {
    expect(personalDashboardAllowed(true)).toBe(true);
    expect(personalDashboardAllowed(false)).toBe(true);
  });
});
