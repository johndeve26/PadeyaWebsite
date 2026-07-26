import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("Logo CLS hardening", () => {
  it("reserves explicit width and height (not width:auto)", () => {
    const src = readFileSync(
      path.join(process.cwd(), "src/components/ui/Logo.tsx"),
      "utf8",
    );
    expect(src).toMatch(/style=\{\{\s*width,\s*height\s*\}\}/);
    expect(src).not.toMatch(/width:\s*["']auto["']/);
    expect(src).not.toMatch(/h-auto w-auto/);
  });
});
