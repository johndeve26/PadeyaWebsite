import { describe, expect, it } from "vitest";

import {
  PLATFORM_REFERRAL_COOKIE_KEY,
  buildAmbassadorReferralLink,
  normalizeAmbassadorCode,
  resolveCheckoutReferral,
} from "./ambassador-referral";

describe("unified referral link helpers", () => {
  it("builds one platform-wide /r/{code} link", () => {
    const link = buildAmbassadorReferralLink("Padeya01", {
      platformWide: true,
      origin: "https://padeya.com",
    });
    expect(link).toBe("https://padeya.com/r/padeya01");
  });

  it("keeps event campaign links event-scoped", () => {
    const link = buildAmbassadorReferralLink("hostcode", {
      slug: "afro-night",
      origin: "https://padeya.com",
    });
    expect(link).toContain("/events/afro-night?ref=hostcode");
    expect(link).not.toContain("/r/");
  });

  it("normalizes referral codes", () => {
    expect(normalizeAmbassadorCode("  AbC ")).toBe("abc");
  });

  it("exposes platform cookie key constant", () => {
    expect(PLATFORM_REFERRAL_COOKIE_KEY).toBe("__platform__");
  });
});

describe("resolveCheckoutReferral shape", () => {
  it("returns platformCode field for dual-code checkout", () => {
    // Without document.cookie in node, empty store → nulls
    const result = resolveCheckoutReferral({
      eventKey: "evt-1",
      explicitCode: "HOST1",
    });
    expect(result.code).toBe("host1");
    expect(result.source).toBe("explicit");
    expect("platformCode" in result).toBe(true);
  });
});
