import { describe, expect, it } from "vitest";

import {
  guessImageContentType,
  inlineMediaPreviewHref,
  isAllowedInlinePreviewUrl,
} from "@/lib/media-preview";

describe("media-preview", () => {
  it("allows padeya CDN image URLs", () => {
    expect(
      isAllowedInlinePreviewUrl(
        "https://media.padeya.com/taxonomy/categories/abc/primary/x.webp",
      ),
    ).toBe(true);
  });

  it("allows relative /media paths with image extensions", () => {
    expect(isAllowedInlinePreviewUrl("/media/taxonomy/x.png")).toBe(true);
  });

  it("rejects non-image and off-host URLs", () => {
    expect(isAllowedInlinePreviewUrl("https://evil.example/x.png")).toBe(false);
    expect(
      isAllowedInlinePreviewUrl("https://media.padeya.com/taxonomy/x.pdf"),
    ).toBe(false);
    expect(isAllowedInlinePreviewUrl("/media/taxonomy/x.bin")).toBe(false);
  });

  it("builds preview href and guesses content types", () => {
    expect(inlineMediaPreviewHref("https://media.padeya.com/a.png")).toBe(
      "/api/media-preview?url=https%3A%2F%2Fmedia.padeya.com%2Fa.png",
    );
    expect(guessImageContentType("https://x/a.webp")).toBe("image/webp");
  });
});
