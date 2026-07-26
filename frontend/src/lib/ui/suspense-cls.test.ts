import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("detail route Suspense CLS guards", () => {
  it("event detail does not use empty Suspense fallback", () => {
    const src = readFileSync(
      path.join(process.cwd(), "src/app/events/[slug]/page.tsx"),
      "utf8",
    );
    expect(src).not.toMatch(/fallback=\{null\}/);
    expect(src).toMatch(/EventDetailSuspenseFallback/);
  });

  it("merch detail does not use empty Suspense fallback", () => {
    const src = readFileSync(
      path.join(process.cwd(), "src/app/merch/[slug]/page.tsx"),
      "utf8",
    );
    expect(src).not.toMatch(/fallback=\{null\}/);
    expect(src).toMatch(/MerchDetailSuspenseFallback/);
  });
});
