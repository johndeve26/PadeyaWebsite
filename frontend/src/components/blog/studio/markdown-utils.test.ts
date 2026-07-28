import { describe, expect, it } from "vitest";

import {
  deleteSection,
  moveSection,
  parseMarkdownH2Sections,
  replaceSectionAt,
  simpleMarkdownToHtml,
} from "@/components/blog/studio/markdown-utils";

describe("blog studio markdown-utils", () => {
  const md = `Intro para

## First

Alpha

## Second

Beta
`;

  it("parses H2 sections", () => {
    const sections = parseMarkdownH2Sections(md);
    expect(sections).toHaveLength(2);
    expect(sections[0].heading).toBe("First");
    expect(sections[1].heading).toBe("Second");
  });

  it("replaces a section body without touching others", () => {
    const next = replaceSectionAt(md, 0, { body: "New alpha" });
    expect(next).toContain("## First");
    expect(next).toContain("New alpha");
    expect(next).toContain("## Second");
    expect(next).toContain("Beta");
  });

  it("moves and deletes sections", () => {
    const moved = moveSection(md, 0, 1);
    const sections = parseMarkdownH2Sections(moved);
    expect(sections[0].heading).toBe("Second");
    expect(sections[1].heading).toBe("First");
    const deleted = deleteSection(moved, 0);
    expect(deleted).not.toContain("## Second");
    expect(deleted).toContain("## First");
  });

  it("renders a simple preview html", () => {
    const html = simpleMarkdownToHtml("## Hello\n\n**world**");
    expect(html).toContain("<h2>");
    expect(html).toContain("<strong>world</strong>");
  });
});
