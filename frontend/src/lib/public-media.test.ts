import { describe, expect, it } from "vitest";

import {
  fromLegacyUrl,
  fromMemoryMedia,
  getMediaAspectRatio,
  getMediaCard,
  getMediaDisplay,
  getMediaFull,
  getMediaOg,
  getMediaThumbnail,
  normalizePublicMedia,
} from "./public-media";

const structuredMedia = {
  id: "asset-1",
  role: "event_banner",
  alt: "Banner",
  focal_x: 0.25,
  focal_y: 0.75,
  width: 1600,
  height: 900,
  url: "https://media.padeya.com/display.webp",
  thumbnail_url: "https://media.padeya.com/thumb.webp",
  card_url: "https://media.padeya.com/card.webp",
  display_url: "https://media.padeya.com/display.webp",
  full_url: "https://media.padeya.com/full.webp",
  og_url: "https://media.padeya.com/og.webp",
  variants: {
    thumbnail: { url: "https://media.padeya.com/thumb.webp", width: 200, height: 112 },
    card: { url: "https://media.padeya.com/card.webp", width: 640, height: 400 },
    display: { url: "https://media.padeya.com/display.webp", width: 1200, height: 675 },
    full: { url: "https://media.padeya.com/full.webp", width: 2400, height: 1350 },
    og: { url: "https://media.padeya.com/og.webp", width: 1200, height: 630 },
  },
};

describe("normalizePublicMedia", () => {
  it("returns null for empty input without legacy", () => {
    expect(normalizePublicMedia(null)).toBeNull();
    expect(normalizePublicMedia(undefined)).toBeNull();
  });

  it("wraps legacy URL strings", () => {
    expect(normalizePublicMedia("https://cdn.example.com/a.jpg")).toEqual({
      url: "https://cdn.example.com/a.jpg",
      display_url: "https://cdn.example.com/a.jpg",
      legacy_url: "https://cdn.example.com/a.jpg",
    });
  });

  it("fills url from legacyUrl when structured media lacks display fields", () => {
    expect(
      normalizePublicMedia({ id: "x" }, "https://cdn.example.com/fallback.jpg"),
    ).toEqual({
      id: "x",
      url: "https://cdn.example.com/fallback.jpg",
      legacy_url: "https://cdn.example.com/fallback.jpg",
    });
  });
});

describe("variant getters", () => {
  it("respects fallback order for thumbnail intent", () => {
    const withoutThumb = {
      ...structuredMedia,
      thumbnail_url: null,
      variants: { ...structuredMedia.variants, thumbnail: undefined },
    };
    expect(getMediaThumbnail(structuredMedia)).toBe(
      "https://media.padeya.com/thumb.webp",
    );
    expect(getMediaThumbnail(withoutThumb)).toBe(
      "https://media.padeya.com/card.webp",
    );
  });

  it("respects fallback order for card intent", () => {
    const withoutCard = {
      ...structuredMedia,
      card_url: null,
      variants: { ...structuredMedia.variants, card: undefined },
    };
    expect(getMediaCard(structuredMedia)).toBe(
      "https://media.padeya.com/card.webp",
    );
    expect(getMediaCard(withoutCard)).toBe(
      "https://media.padeya.com/display.webp",
    );
  });

  it("respects fallback order for display intent", () => {
    const withoutDisplay = {
      ...structuredMedia,
      display_url: null,
      url: null,
      variants: { ...structuredMedia.variants, display: undefined },
    };
    expect(getMediaDisplay(structuredMedia)).toBe(
      "https://media.padeya.com/display.webp",
    );
    expect(getMediaDisplay(withoutDisplay)).toBe(
      "https://media.padeya.com/full.webp",
    );
  });

  it("respects fallback order for full intent (no thumbnail fallback)", () => {
    const withoutFull = {
      ...structuredMedia,
      full_url: null,
      variants: { ...structuredMedia.variants, full: undefined },
    };
    expect(getMediaFull(structuredMedia)).toBe(
      "https://media.padeya.com/full.webp",
    );
    expect(getMediaFull(withoutFull)).toBe(
      "https://media.padeya.com/display.webp",
    );
    expect(
      getMediaFull({
        ...withoutFull,
        display_url: null,
        url: null,
        variants: {
          card: structuredMedia.variants.card,
        },
      }),
    ).toBe("https://media.padeya.com/card.webp");
  });

  it("respects fallback order for og intent", () => {
    const withoutOg = {
      ...structuredMedia,
      og_url: null,
      variants: { ...structuredMedia.variants, og: undefined },
    };
    expect(getMediaOg(structuredMedia)).toBe("https://media.padeya.com/og.webp");
    expect(getMediaOg(withoutOg)).toBe(
      "https://media.padeya.com/display.webp",
    );
  });

  it("falls back to legacyUrl", () => {
    expect(getMediaThumbnail(null, "https://cdn.example.com/legacy.jpg")).toBe(
      "https://cdn.example.com/legacy.jpg",
    );
  });
});

describe("fromLegacyUrl / fromMemoryMedia", () => {
  it("builds legacy media objects", () => {
    expect(fromLegacyUrl("")).toBeNull();
    expect(fromLegacyUrl(null)).toBeNull();
    expect(fromLegacyUrl("https://cdn.example.com/x.jpg")).toEqual({
      url: "https://cdn.example.com/x.jpg",
      display_url: "https://cdn.example.com/x.jpg",
      legacy_url: "https://cdn.example.com/x.jpg",
    });
  });

  it("maps memory photo fields to public media", () => {
    const media = fromMemoryMedia({
      url: "https://media.padeya.com/full.jpg",
      thumbnail_url: "https://media.padeya.com/thumb.jpg",
      width: 1200,
      height: 800,
      caption: "Crowd shot",
    });
    expect(getMediaThumbnail(media)).toBe("https://media.padeya.com/thumb.jpg");
    expect(getMediaFull(media)).toBe("https://media.padeya.com/full.jpg");
    expect(media.alt).toBe("Crowd shot");
  });
});

describe("getMediaAspectRatio", () => {
  it("uses top-level dimensions when present", () => {
    expect(getMediaAspectRatio(structuredMedia)).toBeCloseTo(1600 / 900);
  });

  it("falls back to variant dimensions", () => {
    expect(
      getMediaAspectRatio({
        variants: {
          display: { url: "x", width: 800, height: 400 },
        },
      }),
    ).toBe(2);
  });

  it("returns null when dimensions are missing", () => {
    expect(getMediaAspectRatio({ url: "x" })).toBeNull();
  });
});
