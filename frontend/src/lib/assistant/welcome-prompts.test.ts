import { describe, expect, it } from "vitest";

import {
  getWelcomePrompts,
  resolveWelcomeRole,
} from "@/lib/assistant/welcome-prompts";

describe("welcome prompts", () => {
  it("resolves known roles", () => {
    expect(resolveWelcomeRole("host")).toBe("host");
    expect(resolveWelcomeRole("ADMIN")).toBe("admin");
    expect(resolveWelcomeRole(null)).toBe("public");
    expect(resolveWelcomeRole("unknown")).toBe("public");
  });

  it("returns role-aware suggested prompts", () => {
    const publicPrompts = getWelcomePrompts("public");
    expect(publicPrompts.length).toBeGreaterThan(0);
    expect(publicPrompts.some((p) => /ibadan|free events|ambassador|support/i.test(p.label))).toBe(
      true,
    );

    const hostPrompts = getWelcomePrompts("host");
    expect(hostPrompts.some((p) => /event|draft|sales|legacy/i.test(p.label))).toBe(true);

    const adminPrompts = getWelcomePrompts("admin");
    expect(adminPrompts.some((p) => /admin|taxonomy|reporting|liabilit/i.test(p.label))).toBe(
      true,
    );
  });
});
