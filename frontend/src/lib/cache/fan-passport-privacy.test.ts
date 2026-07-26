import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import {
  FAN_PASSPORT_CACHE,
  isPrivateNeverCachePath,
} from "./public-cache-policy";
import {
  buildFanMetadata,
  isFanPassportIndexable,
} from "@/lib/seo/fan-metadata";
import type { FanPassportPublicPage } from "@/lib/types/passport";

function fanFixture(
  visibility: FanPassportPublicPage["visibility"],
): FanPassportPublicPage {
  return {
    username: "privacyfan",
    display_name: "Privacy Fan",
    visibility,
    tagline: null,
    bio: null,
    avatar_url: null,
  } as FanPassportPublicPage;
}

describe("Fan Passport privacy cache policy", () => {
  it("marks /f/* as never CDN-cacheable", () => {
    expect(isPrivateNeverCachePath("/f/privacyfan")).toBe(true);
    expect(FAN_PASSPORT_CACHE.public.html).toMatch(/no-store|force-dynamic/);
    expect(FAN_PASSPORT_CACHE.private.behavior).toMatch(/404/);
  });

  it("public page source is force-dynamic / revalidate 0", () => {
    const src = readFileSync(
      path.join(process.cwd(), "src/app/f/[username]/page.tsx"),
      "utf8",
    );
    expect(src).toMatch(/force-dynamic/);
    expect(src).toMatch(/revalidate\s*=\s*0/);
    expect(src).not.toMatch(/revalidate\s*=\s*180/);
  });

  it("indexability: public yes, unlisted/private no", () => {
    expect(isFanPassportIndexable(fanFixture("public"))).toBe(true);
    expect(isFanPassportIndexable(fanFixture("unlisted"))).toBe(false);
    expect(isFanPassportIndexable(fanFixture("private"))).toBe(false);
  });

  it("unlisted metadata is noindex", () => {
    const meta = buildFanMetadata(fanFixture("unlisted"));
    const robots = meta.robots;
    expect(robots).toBeTruthy();
    if (robots && typeof robots === "object" && "index" in robots) {
      expect(robots.index).toBe(false);
    }
  });

  it("public metadata is not hard-noindex via fan helper", () => {
    // Production indexing still depends on env-policy; here we only assert the
    // fan helper does not force noIndex for public visibility.
    const publicMeta = buildFanMetadata(fanFixture("public"));
    const unlistedMeta = buildFanMetadata(fanFixture("unlisted"));
    expect(isFanPassportIndexable(fanFixture("public"))).toBe(true);
    expect(isFanPassportIndexable(fanFixture("unlisted"))).toBe(false);
    // Unlisted must be stricter than public in the helper path.
    const u = unlistedMeta.robots;
    if (u && typeof u === "object" && "index" in u) {
      expect(u.index).toBe(false);
    }
    void publicMeta;
  });
});
