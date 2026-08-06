import { describe, expect, it } from "vitest";

import {
  parseAssistantInline,
  splitMarkdownLinks,
} from "@/lib/assistant/markdown-parse";

describe("assistant markdown-parse", () => {
  it("parses markdown links as label + href, not raw syntax", () => {
    const segments = parseAssistantInline(
      "Contact [Support](https://padeya.com/support).",
    );
    expect(segments).toEqual([
      { type: "text", value: "Contact " },
      {
        type: "link",
        label: "Support",
        href: "https://padeya.com/support",
      },
      { type: "text", value: "." },
    ]);
  });

  it("parses relative markdown links", () => {
    const segments = parseAssistantInline("See [Help Center](/help).");
    expect(segments).toEqual([
      { type: "text", value: "See " },
      { type: "link", label: "Help Center", href: "/help" },
      { type: "text", value: "." },
    ]);
  });

  it("does not treat markdown URL as a bare link", () => {
    const blocks = splitMarkdownLinks(
      "[Support](https://padeya.com/support)",
    );
    expect(blocks).toEqual([
      {
        type: "link",
        label: "Support",
        href: "https://padeya.com/support",
        raw: "[Support](https://padeya.com/support)",
      },
    ]);
  });

  it("parses multiple markdown links in one line", () => {
    const segments = parseAssistantInline(
      "[Help Center](/help) or [Support](https://padeya.com/support)",
    );
    expect(segments.filter((s) => s.type === "link")).toEqual([
      { type: "link", label: "Help Center", href: "/help" },
      {
        type: "link",
        label: "Support",
        href: "https://padeya.com/support",
      },
    ]);
  });
});
