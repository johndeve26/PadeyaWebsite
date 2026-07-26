import { describe, expect, it } from "vitest";

import {
  isOptimizableMediaSrc,
  isSvgMediaSrc,
  MEDIA_SIZES,
  resolveMediaSizes,
} from "./media-image";

describe("media-image helpers", () => {
  it("detects SVG sources", () => {
    expect(isSvgMediaSrc("/demo/cover.svg")).toBe(true);
    expect(isSvgMediaSrc("https://padeya.com/media/x.png")).toBe(false);
  });

  it("allows same-origin media and trusted hosts only", () => {
    expect(isOptimizableMediaSrc("/media/covers/a.jpg")).toBe(true);
    expect(isOptimizableMediaSrc("/brand/logo.png")).toBe(true);
    expect(
      isOptimizableMediaSrc(
        "https://padeyawebsite.onrender.com/media/covers/a.jpg",
      ),
    ).toBe(true);
    expect(
      isOptimizableMediaSrc(
        "https://media.padeya.com/memories/events/abc/photo.webp",
      ),
    ).toBe(true);
    expect(isOptimizableMediaSrc("https://evil.example/media/x.jpg")).toBe(
      false,
    );
    expect(isOptimizableMediaSrc("/demo/cover.svg")).toBe(false);
  });

  it("resolves size presets used by public cards/heroes", () => {
    expect(resolveMediaSizes("hero")).toBe(MEDIA_SIZES.hero);
    expect(resolveMediaSizes("eventCard")).toBe(MEDIA_SIZES.eventCard);
    expect(resolveMediaSizes("(max-width: 640px) 100vw")).toBe(
      "(max-width: 640px) 100vw",
    );
  });

  it("event card sizes are not full-viewport-only", () => {
    expect(MEDIA_SIZES.eventCard).toMatch(/33vw|50vw/);
    expect(MEDIA_SIZES.eventCard).not.toBe("100vw");
  });
});
