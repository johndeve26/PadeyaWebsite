import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("next/image remotePatterns", () => {
  it("allows only trusted media hosts (no hostname wildcards)", () => {
    const src = readFileSync(
      path.join(process.cwd(), "next.config.ts"),
      "utf8",
    );
    expect(src).toMatch(/remotePatterns/);
    expect(src).toMatch(/padeyawebsite\.onrender\.com/);
    expect(src).toMatch(/padeya\.com/);
    expect(src).not.toMatch(/hostname:\s*"\*\*"/);
    expect(src).not.toMatch(/hostname:\s*'\*\*'/);
  });
});
