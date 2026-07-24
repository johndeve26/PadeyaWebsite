import { describe, expect, it } from "vitest";

import {
  directoryCardCtas,
  fanPageCtaMode,
  fanPageCtas,
  isOwnFanPassport,
} from "./own-fan-ctas";

describe("own Fan Passport CTAs", () => {
  it("detects own passport by user id (case-insensitive)", () => {
    const id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
    expect(isOwnFanPassport(id, id)).toBe(true);
    expect(isOwnFanPassport(id.toUpperCase(), id)).toBe(true);
    expect(
      isOwnFanPassport(id, "ffffffff-bbbb-cccc-dddd-eeeeeeeeeeee"),
    ).toBe(false);
    expect(isOwnFanPassport(null, id)).toBe(false);
    expect(isOwnFanPassport(id, null)).toBe(false);
    expect(isOwnFanPassport(undefined, undefined)).toBe(false);
  });

  it("own Passport hides Connect button", () => {
    const ctas = fanPageCtas(fanPageCtaMode(true));
    expect(ctas.showConnect).toBe(false);
    expect(ctas.showConnectionRequest).toBe(false);
  });

  it("own Passport hides Message button", () => {
    const ctas = fanPageCtas(fanPageCtaMode(true));
    expect(ctas.showMessage).toBe(false);
    expect(ctas.showFanToFanMessage).toBe(false);
  });

  it('own Passport shows "This is your Fan Passport"', () => {
    const ctas = fanPageCtas(fanPageCtaMode(true));
    expect(ctas.title).toBe("This is your Fan Passport");
    expect(ctas.description).toBe(
      "Preview how your public fan identity appears on Pàdéyá.",
    );
  });

  it("own Passport shows Edit Passport", () => {
    const ctas = fanPageCtas(fanPageCtaMode(true));
    expect(ctas.primary).toEqual({
      label: "Edit Passport",
      href: "/dashboard/passport/settings",
    });
    expect(ctas.allowEdit).toBe(true);
  });

  it("own Passport shows Personal dashboard", () => {
    const ctas = fanPageCtas(fanPageCtaMode(true));
    expect(ctas.secondary).toEqual({
      label: "Personal dashboard",
      href: "/dashboard",
    });
  });

  it("own Passport shows Share profile and hides report/block/follow", () => {
    const ctas = fanPageCtas(fanPageCtaMode(true));
    expect(ctas.share).toEqual({ label: "Share profile" });
    expect(ctas.allowShare).toBe(true);
    expect(ctas.showFollow).toBe(false);
    expect(ctas.showReport).toBe(false);
    expect(ctas.showBlock).toBe(false);
  });

  it("other user Passport still shows Connect/Message where allowed", () => {
    const ctas = fanPageCtas(fanPageCtaMode(false));
    expect(ctas.showConnect).toBe(true);
    expect(ctas.showMessage).toBe(true);
    expect(ctas.showConnectionRequest).toBe(true);
    expect(ctas.showFanToFanMessage).toBe(true);
    expect(ctas.showReport).toBe(true);
    expect(ctas.showBlock).toBe(true);
    expect(ctas.primary).toBeNull();
    expect(ctas.title).toBeNull();
    expect(ctas.share).toBeNull();
    expect(ctas.allowEdit).toBe(false);
  });

  it('fan directory card for current user shows "You" and hides self-actions', () => {
    const ctas = directoryCardCtas(true, "/f/ada");
    expect(ctas.youBadge).toBe("You");
    expect(ctas.showConnect).toBe(false);
    expect(ctas.showMessage).toBe(false);
    expect(ctas.showReport).toBe(false);
    expect(ctas.showBlock).toBe(false);
    expect(ctas.edit).toEqual({
      label: "Edit Passport",
      href: "/dashboard/passport/settings",
    });
    expect(ctas.view).toEqual({
      label: "View Passport",
      href: "/f/ada",
    });
  });

  it("other directory card keeps Connect/Message/Report/Block", () => {
    const ctas = directoryCardCtas(false, "/f/other");
    expect(ctas.youBadge).toBeNull();
    expect(ctas.showConnect).toBe(true);
    expect(ctas.showMessage).toBe(true);
    expect(ctas.showReport).toBe(true);
    expect(ctas.showBlock).toBe(true);
    expect(ctas.edit).toBeNull();
    expect(ctas.view?.label).toBe("View Passport");
  });
});
