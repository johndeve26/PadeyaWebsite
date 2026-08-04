import { describe, expect, it } from "vitest";

import {
  canArchiveBlogPost,
  canPublishBlogPost,
  canUnpublishBlogPost,
  isBlogPostArchived,
} from "@/lib/blog-admin-lifecycle";

describe("blog admin post lifecycle", () => {
  it("treats archived status as archived", () => {
    expect(isBlogPostArchived({ status: "archived" })).toBe(true);
    expect(canArchiveBlogPost({ status: "archived" })).toBe(false);
    expect(canPublishBlogPost({ status: "archived" })).toBe(false);
    expect(canUnpublishBlogPost({ status: "archived" })).toBe(false);
  });

  it("treats archived_at as archived even when status lags", () => {
    expect(
      isBlogPostArchived({ status: "draft", archived_at: "2026-01-01T00:00:00Z" }),
    ).toBe(true);
    expect(
      canArchiveBlogPost({ status: "draft", archived_at: "2026-01-01T00:00:00Z" }),
    ).toBe(false);
  });

  it("allows archive/publish on active drafts", () => {
    expect(canArchiveBlogPost({ status: "draft" })).toBe(true);
    expect(canPublishBlogPost({ status: "draft" })).toBe(true);
    expect(canUnpublishBlogPost({ status: "draft" })).toBe(false);
  });

  it("allows unpublish but not publish on active published posts", () => {
    expect(canArchiveBlogPost({ status: "published" })).toBe(true);
    expect(canPublishBlogPost({ status: "published" })).toBe(false);
    expect(canUnpublishBlogPost({ status: "published" })).toBe(true);
  });
});
