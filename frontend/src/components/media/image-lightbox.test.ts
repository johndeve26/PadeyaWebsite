import { describe, expect, it } from "vitest";

import {
  ENLARGE_ALT_ATTR,
  ENLARGE_SRC_ATTR,
  enlargeableAttrs,
} from "@/components/media/ImageLightbox";

describe("enlargeableAttrs", () => {
  it("marks a resolvable image for the lightbox", () => {
    const attrs = enlargeableAttrs("/media/avatar.jpg", "Ada");
    expect(attrs?.[ENLARGE_SRC_ATTR]).toContain("avatar.jpg");
    expect(attrs?.[ENLARGE_ALT_ATTR]).toBe("Ada");
  });

  it("returns undefined for empty src", () => {
    expect(enlargeableAttrs(null)).toBeUndefined();
    expect(enlargeableAttrs("")).toBeUndefined();
  });

  it("uses enlargeSrc for lightbox when provided", () => {
    const attrs = enlargeableAttrs(
      "https://cdn.example.com/thumb.jpg",
      "Preview",
      "https://cdn.example.com/full.jpg",
    );
    expect(attrs?.[ENLARGE_SRC_ATTR]).toBe("https://cdn.example.com/full.jpg");
    expect(attrs?.[ENLARGE_ALT_ATTR]).toBe("Preview");
  });
});
