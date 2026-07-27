import { describe, expect, it } from "vitest";

import { enforcePadeyaDemoAssetUrl, resolveMediaUrl } from "./media";

describe("resolveMediaUrl / enforcePadeyaDemoAssetUrl", () => {
  it("rewrites smartlance demo hosts to https://padeya.com", () => {
    expect(
      resolveMediaUrl(
        "https://padeya.smartlancedesigns.com/demo/events/mainland-vibes-summer.svg",
      ),
    ).toBe("https://padeya.com/demo/events/mainland-vibes-summer.svg");
    expect(
      enforcePadeyaDemoAssetUrl(
        "http://www.padeya.smartlancedesigns.com/demo/events/afrobeats-night-live.svg",
      ),
    ).toBe("https://padeya.com/demo/events/afrobeats-night-live.svg");
  });

  it("absolutizes site-relative /demo/ assets onto padeya.com", () => {
    expect(resolveMediaUrl("/demo/events/mainland-vibes-summer.svg")).toBe(
      "https://padeya.com/demo/events/mainland-vibes-summer.svg",
    );
  });

  it("never leaves smartlancedesigns.com in resolved output", () => {
    const samples = [
      "https://padeya.smartlancedesigns.com/demo/events/x.svg",
      "//padeya.smartlancedesigns.com/demo/hosts/y-avatar.svg",
      "/demo/events/z.svg",
    ];
    for (const src of samples) {
      const out = resolveMediaUrl(src);
      expect(out).not.toMatch(/smartlancedesigns\.com/i);
      expect(out.startsWith("https://padeya.com/demo/")).toBe(true);
    }
  });

  it("leaves non-demo absolute media hosts alone", () => {
    expect(
      resolveMediaUrl("https://media.padeya.com/memories/events/abc/photo.webp"),
    ).toBe("https://media.padeya.com/memories/events/abc/photo.webp");
    expect(resolveMediaUrl("https://cdn.example.com/poster.jpg")).toBe(
      "https://cdn.example.com/poster.jpg",
    );
  });
});
