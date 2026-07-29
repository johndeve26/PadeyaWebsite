import { describe, expect, it } from "vitest";

import { BLOG_CONTENT_TYPES } from "@/components/blog/studio/types";

describe("blog taxonomy studio constants", () => {
  it("keeps deprecated content types as fallback metadata only", () => {
    expect(BLOG_CONTENT_TYPES.length).toBeGreaterThan(5);
    expect(BLOG_CONTENT_TYPES).toContain("How-to guide");
  });
});
