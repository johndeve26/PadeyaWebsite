import { describe, it, expect } from "vitest";
import {
  validateTab,
  autosaveStatusText,
  computeChecklist,
  seoTitleScore,
  seoDescriptionScore,
  type WorkspaceTab,
} from "./blog-workspace";
import { cloneDocument, createBlock, defaultDocument, type BlogContentDocument } from "./blog-document";

describe("validateTab", () => {
  it("returns valid tab as-is", () => {
    const tabs: WorkspaceTab[] = ["plan", "write", "design", "seo", "review", "publish"];
    for (const tab of tabs) {
      expect(validateTab(tab)).toBe(tab);
    }
  });

  it("falls back to 'write' for invalid values", () => {
    expect(validateTab("invalid")).toBe("write");
    expect(validateTab(null)).toBe("write");
    expect(validateTab(undefined)).toBe("write");
    expect(validateTab("")).toBe("write");
  });
});

describe("autosaveStatusText", () => {
  it("returns correct text for each status", () => {
    expect(autosaveStatusText("saving")).toBe("Saving…");
    expect(autosaveStatusText("saved")).toBe("Saved");
    expect(autosaveStatusText("failed")).toBe("Save failed");
    expect(autosaveStatusText("conflict")).toBe("Conflict");
    expect(autosaveStatusText("idle")).toBe("");
  });
});

describe("computeChecklist", () => {
  const emptyPost = {
    title: "",
    slug: "",
    seoTitle: "",
    seoDescription: "",
    focusKeyword: "",
  };

  const fullPost = {
    title: "My great article",
    slug: "my-great-article",
    seoTitle: "My Great Article Title",
    seoDescription: "A description of my article that is long enough to pass the minimum character count requirement here.",
    focusKeyword: "great",
  };

  it("marks most items as not ok for empty post", () => {
    const items = computeChecklist(emptyPost, { blocks: [] });
    // title, meta_title, meta_desc, slug, keyword_title should all fail
    const failIds = ["title", "meta_title", "meta_desc", "slug", "keyword_title"];
    for (const id of failIds) {
      const item = items.find((i) => i.id === id);
      expect(item?.ok, `Expected ${id} to be not ok`).toBe(false);
    }
  });

  it("marks title ok when title is present", () => {
    const items = computeChecklist(fullPost, { blocks: [] });
    const titleItem = items.find((i) => i.id === "title");
    expect(titleItem?.ok).toBe(true);
  });

  it("marks h2 ok when document has h2 block", () => {
    const items = computeChecklist(fullPost, {
      blocks: [{ type: "heading", props: { level: 2 } }],
    });
    const h2Item = items.find((i) => i.id === "h2");
    expect(h2Item?.ok).toBe(true);
  });

  it("marks image_alt as not ok when image missing alt", () => {
    const items = computeChecklist(fullPost, {
      blocks: [{ type: "image", props: {} }],
    });
    const altItem = items.find((i) => i.id === "image_alt");
    expect(altItem?.ok).toBe(false);
  });

  it("marks image_alt ok when all images have alt", () => {
    const items = computeChecklist(fullPost, {
      blocks: [{ type: "image", props: { alt: "A nice image" } }],
    });
    const altItem = items.find((i) => i.id === "image_alt");
    expect(altItem?.ok).toBe(true);
  });

  it("marks keyword_title ok when keyword is in title", () => {
    const items = computeChecklist(fullPost, { blocks: [] });
    const kwItem = items.find((i) => i.id === "keyword_title");
    expect(kwItem?.ok).toBe(true);
  });

  it("marks keyword_title not ok when keyword not in title", () => {
    const items = computeChecklist(
      { ...fullPost, focusKeyword: "completely-different" },
      { blocks: [] },
    );
    const kwItem = items.find((i) => i.id === "keyword_title");
    expect(kwItem?.ok).toBe(false);
  });
});

describe("seoTitleScore", () => {
  it("fails for empty string", () => {
    expect(seoTitleScore("").ok).toBe(false);
  });

  it("fails for short title", () => {
    expect(seoTitleScore("Short").ok).toBe(false);
  });

  it("passes for 55 char title", () => {
    const title = "A".repeat(55);
    expect(seoTitleScore(title).ok).toBe(true);
  });

  it("fails for title over 60 chars", () => {
    const title = "A".repeat(61);
    expect(seoTitleScore(title).ok).toBe(false);
  });
});

describe("seoDescriptionScore", () => {
  it("fails for empty string", () => {
    expect(seoDescriptionScore("").ok).toBe(false);
  });

  it("fails for short description", () => {
    expect(seoDescriptionScore("Too short").ok).toBe(false);
  });

  it("passes for 140 char description", () => {
    const desc = "A".repeat(140);
    expect(seoDescriptionScore(desc).ok).toBe(true);
  });

  it("fails for description over 160 chars", () => {
    const desc = "A".repeat(161);
    expect(seoDescriptionScore(desc).ok).toBe(false);
  });
});

describe("shared document history contract", () => {
  it("undo stack restores prior cloned snapshots (Write/Design shared model)", () => {
    let current = defaultDocument();
    const past: BlogContentDocument[] = [];
    const apply = (next: BlogContentDocument) => {
      past.push(cloneDocument(current));
      current = cloneDocument(next);
    };
    const undo = () => {
      const prev = past.pop();
      if (prev) current = cloneDocument(prev);
    };

    apply({
      ...current,
      blocks: [createBlock("rich_text", { content: { markdown: "Paragraph A" } })],
    });
    apply({
      ...current,
      blocks: [
        ...current.blocks,
        createBlock("heading", { content: { text: "Heading B", level: 2 } }),
      ],
    });
    expect(current.blocks).toHaveLength(2);
    undo();
    expect(current.blocks).toHaveLength(1);
    expect(current.blocks[0]?.content.markdown).toBe("Paragraph A");
  });
});
