import { describe, expect, it } from "vitest";

import {
  cloneDocument,
  createBlock,
  defaultDocument,
  documentToMarkdown,
  extractOutline,
  insertBlockAtRoot,
  parseContentDocument,
  removeBlockFromTree,
  updateBlockInTree,
} from "@/lib/blog-document";

describe("blog document utilities", () => {
  it("creates a blank document with one rich_text block", () => {
    const doc = defaultDocument();
    expect(doc.version).toBe(1);
    expect(doc.blocks).toHaveLength(1);
    expect(doc.blocks[0].type).toBe("rich_text");
  });

  it("parses legacy body into legacy_rich_text block", () => {
    const doc = parseContentDocument(null, "## Hello\n\nWorld");
    expect(doc.blocks[0].type).toBe("legacy_rich_text");
    expect(doc.blocks[0].content.markdown).toContain("Hello");
  });

  it("inserts and removes blocks", () => {
    const doc = defaultDocument();
    const heading = createBlock("heading");
    const next = insertBlockAtRoot(doc.blocks, heading, 0);
    expect(next).toHaveLength(2);
    const removed = removeBlockFromTree(next, heading.id);
    expect(removed).toHaveLength(1);
  });

  it("updates block in nested tree", () => {
    const section = createBlock("standard_section");
    let doc = defaultDocument();
    doc = { ...doc, blocks: [section] };
    const childId = section.children[0].id;
    const updated = updateBlockInTree(doc.blocks, childId, (b) => ({
      ...b,
      content: { ...b.content, markdown: "Updated" },
    }));
    expect(updated[0].children[0].content.markdown).toBe("Updated");
  });

  it("extracts outline from headings", () => {
    const doc = defaultDocument();
    doc.blocks = [
      createBlock("heading", {
        content: { text: "Intro", level: 2 },
      }),
      createBlock("heading", {
        content: { text: "Details", level: 3 },
      }),
    ];
    const outline = extractOutline(doc.blocks);
    expect(outline).toHaveLength(2);
    expect(outline[0].text).toBe("Intro");
  });

  it("clones document with fresh block ids", () => {
    const doc = defaultDocument();
    const cloned = cloneDocument(doc);
    expect(cloned.blocks[0].id).not.toBe(doc.blocks[0].id);
  });

  it("flattens document to markdown", () => {
    const doc = defaultDocument();
    doc.blocks[0].content.markdown = "Hello world";
    const md = documentToMarkdown(doc);
    expect(md).toContain("Hello world");
  });
});
