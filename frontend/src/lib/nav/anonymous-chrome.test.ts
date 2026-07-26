import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("anonymous public nav chrome", () => {
  it("dynamically loads authenticated header extras", () => {
    const src = readFileSync(
      path.join(process.cwd(), "src/components/layout/SiteHeader.tsx"),
      "utf8",
    );
    expect(src).toMatch(/dynamic\(/);
    expect(src).toMatch(/NotificationBell/);
    expect(src).toMatch(/HeaderUserMenu/);
    // Must not statically import the heavy notification module into the header graph.
    expect(src).not.toMatch(
      /import\s+\{\s*NotificationBell\s*\}\s+from\s+"@\/components\/notifications\/NotificationBell"/,
    );
    expect(src).not.toMatch(
      /import\s+\{\s*HeaderUserMenu\s*\}\s+from\s+"@\/components\/layout\/HeaderUserMenu"/,
    );
  });

  it("defers check-in QR library behind dynamic import", () => {
    const src = readFileSync(
      path.join(process.cwd(), "src/components/checkin/CheckInWorkspace.tsx"),
      "utf8",
    );
    expect(src).toMatch(/dynamic\(/);
    expect(src).toMatch(/QrScanner/);
    expect(src).not.toMatch(
      /import\s+\{\s*QrScanner\s*\}\s+from\s+"@\/components\/checkin\/QrScanner"/,
    );
  });
});
