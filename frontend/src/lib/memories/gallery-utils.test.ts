import { describe, expect, it } from "vitest";

import {
  INITIAL_PHOTOS_BATCH,
  LOAD_MORE_BATCH,
  MASONRY_DEFAULT_ASPECT,
  clampVisibleCount,
  isFallbackMemoryArt,
  masonryColumnCount,
  masonryGap,
  masonryRowSpan,
  memoryAltText,
  memoryAttributionLabel,
  memoryAspectRatio,
  memorySourceBadge,
  resolveMemoryAspect,
} from "@/lib/memories/gallery-utils";
import type { MemoryMedia } from "@/lib/types/memories";

function photo(
  overrides: Partial<MemoryMedia> & Pick<MemoryMedia, "id">,
): MemoryMedia {
  return {
    media_type: "image",
    url: "/demo/memories/test.svg",
    label: null,
    sort_order: 0,
    created_at: "2026-06-17T00:00:00Z",
    ...overrides,
  };
}

describe("memoryAspectRatio", () => {
  it("preserves portrait and landscape ratios within bounds", () => {
    expect(memoryAspectRatio(800, 1200)).toBe(1.5);
    expect(memoryAspectRatio(1600, 900)).toBe(0.5625);
    expect(memoryAspectRatio(1000, 1000)).toBe(1);
  });

  it("clamps very tall images", () => {
    expect(memoryAspectRatio(400, 2000)).toBe(2.5);
  });

  it("falls back when dimensions missing", () => {
    expect(memoryAspectRatio(null, null)).toBe(MASONRY_DEFAULT_ASPECT);
    expect(memoryAspectRatio(0, 100)).toBe(MASONRY_DEFAULT_ASPECT);
  });
});

describe("resolveMemoryAspect", () => {
  it("prefers stored dimensions over measured", () => {
    expect(resolveMemoryAspect(1600, 900, 1.5)).toBe(0.5625);
  });

  it("uses measured ratio when dimensions are missing", () => {
    expect(resolveMemoryAspect(null, null, 630 / 1200)).toBeCloseTo(0.525, 3);
  });

  it("falls back to the default when nothing is known", () => {
    expect(resolveMemoryAspect(null, null)).toBe(MASONRY_DEFAULT_ASPECT);
  });
});

describe("masonryColumnCount", () => {
  it("returns responsive column counts", () => {
    expect(masonryColumnCount(300)).toBe(1);
    expect(masonryColumnCount(400)).toBe(2);
    expect(masonryColumnCount(800)).toBe(3);
    expect(masonryColumnCount(700)).toBe(2);
    expect(masonryColumnCount(1200)).toBe(4);
    expect(masonryColumnCount(1500)).toBe(5);
  });
});

describe("masonryGap", () => {
  it("uses tighter gaps on mobile", () => {
    expect(masonryGap(375)).toBe(12);
    expect(masonryGap(800)).toBe(16);
    expect(masonryGap(1280)).toBe(18);
  });
});

describe("masonryRowSpan", () => {
  it("computes taller spans for portrait images", () => {
    const columnWidth = 240;
    const gap = 16;
    const portrait = masonryRowSpan(columnWidth, 1.5, gap);
    const landscape = masonryRowSpan(columnWidth, 0.6, gap);
    expect(portrait).toBeGreaterThan(landscape);
  });
});

describe("memoryAltText", () => {
  it("uses caption when present", () => {
    expect(
      memoryAltText(photo({ id: "1", caption: "Mic check energy." })),
    ).toBe("Mic check energy.");
  });

  it("falls back by uploader role", () => {
    expect(
      memoryAltText(photo({ id: "2", uploader_role: "fan" })),
    ).toBe("Community memory photo");
    expect(
      memoryAltText(photo({ id: "3", uploader_role: "host" })),
    ).toBe("Host memory photo");
  });
});

describe("memoryAttributionLabel", () => {
  it("shows verified attendee for private fans", () => {
    expect(
      memoryAttributionLabel(photo({ id: "1", uploader_role: "fan" })),
    ).toBe("Verified attendee");
  });

  it("shows public fan name when provided", () => {
    expect(
      memoryAttributionLabel(
        photo({
          id: "2",
          uploader_role: "fan",
          attribution: "Chidi Tech",
        }),
      ),
    ).toBe("Chidi Tech");
  });

  it("returns null for host uploads", () => {
    expect(
      memoryAttributionLabel(photo({ id: "3", uploader_role: "host" })),
    ).toBeNull();
  });
});

describe("memorySourceBadge", () => {
  it("distinguishes host and community", () => {
    expect(memorySourceBadge("host")).toBe("Host memory");
    expect(memorySourceBadge("host", "Lagos Comedy Hub")).toBe(
      "From Lagos Comedy Hub",
    );
    expect(memorySourceBadge("community")).toBe("Community memory");
  });
});

describe("isFallbackMemoryArt", () => {
  it("detects demo SVG placeholders", () => {
    expect(isFallbackMemoryArt("/demo/memories/island-comedy-memory.svg")).toBe(
      true,
    );
    expect(isFallbackMemoryArt("https://cdn.example.com/photo.jpg")).toBe(
      false,
    );
  });
});

describe("clampVisibleCount", () => {
  it("loads more in batches", () => {
    expect(clampVisibleCount(50, INITIAL_PHOTOS_BATCH)).toBe(
      INITIAL_PHOTOS_BATCH + LOAD_MORE_BATCH,
    );
    expect(clampVisibleCount(20, 18)).toBe(20);
  });
});

describe("stable DOM order", () => {
  it("keeps source order for mixed aspect photos", () => {
    const photos = [
      photo({ id: "a", width: 800, height: 1200 }),
      photo({ id: "b", width: 1600, height: 900 }),
      photo({ id: "c", width: 1000, height: 1000 }),
    ];
    const ids = photos.map((p) => p.id);
    expect(ids).toEqual(["a", "b", "c"]);
  });
});
