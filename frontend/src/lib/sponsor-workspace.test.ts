import { describe, expect, it } from "vitest";

import {
  flatSponsorNav,
  userHasSponsorWorkspace,
} from "@/lib/nav/sponsor-nav";

describe("sponsor nav", () => {
  it("includes workspace routes", async () => {
    const hrefs = flatSponsorNav().map((i) => i.href);
    expect(hrefs).toContain("/sponsor");
    expect(hrefs).toContain("/sponsor/opportunities");
    expect(hrefs).toContain("/sponsor/inquiries");
    expect(hrefs).toContain("/sponsor/saved");
    expect(hrefs).toContain("/sponsor/campaigns");
    expect(hrefs).toContain("/sponsor/deals");
    const fs = await import("node:fs/promises");
    const dealPage = await fs.readFile(
      new URL("../app/sponsor/deals/page.tsx", import.meta.url),
      "utf8",
    );
    expect(dealPage).toMatch(/export default/);
    expect(hrefs).toContain("/sponsor/reports");
  });
});

describe("userHasSponsorWorkspace", () => {
  it("is false without workspaces", () => {
    expect(userHasSponsorWorkspace([])).toBe(false);
    expect(userHasSponsorWorkspace(null)).toBe(false);
  });

  it("is true when user has a sponsor workspace", () => {
    expect(userHasSponsorWorkspace([{ sponsor_id: "abc" }])).toBe(true);
  });
});

describe("workspace switcher sponsor visibility", () => {
  it("documents sponsor opt-in in switcher source", async () => {
    const fs = await import("node:fs/promises");
    const src = await fs.readFile(
      new URL("../components/hosts/WorkspaceSwitcher.tsx", import.meta.url),
      "utf8",
    );
    expect(src).toMatch(/Sponsor workspaces/);
    expect(src).toMatch(/sponsor:/);
  });
});

describe("sponsor onboarding route", () => {
  it("create page exists", async () => {
    const fs = await import("node:fs/promises");
    const src = await fs.readFile(
      new URL("../app/sponsor/create/page.tsx", import.meta.url),
      "utf8",
    );
    expect(src).toMatch(/createSponsorProfile/);
    expect(src).toMatch(/submit_for_review/);
  });
});

describe("public sponsor profile route", () => {
  it("loads public profile by slug", async () => {
    const fs = await import("node:fs/promises");
    const src = await fs.readFile(
      new URL("../app/sponsors/[slug]/page.tsx", import.meta.url),
      "utf8",
    );
    expect(src).toMatch(/getPublicSponsorBySlug/);
    expect(src).toMatch(/SponsorProfileClient/);
  });

  it("renders rich sections and host CTAs", async () => {
    const fs = await import("node:fs/promises");
    const view = await fs.readFile(
      new URL(
        "../components/sponsors/PublicSponsorProfileView.tsx",
        import.meta.url,
      ),
      "utf8",
    );
    expect(view).toMatch(/Public campaigns & case studies/);
    expect(view).toMatch(/Sponsored events & placements/);
    expect(view).toMatch(/Hosts they have partnered with/);
    expect(view).toMatch(/No public campaigns yet/);
    expect(view).toMatch(/Log in to pitch this sponsor/);
    expect(view).toMatch(/Send sponsorship inquiry/);
    const cards = await fs.readFile(
      new URL(
        "../components/sponsors/SponsorPublicProfileCards.tsx",
        import.meta.url,
      ),
      "utf8",
    );
    expect(cards).toMatch(/View event/);
    expect(cards).toMatch(/View host/);
    expect(cards).toMatch(/formatDate/);
    expect(cards).toMatch(/linked_sponsored_events_count/);
    expect(cards).toMatch(/sponsored_events_together/);
  });

  it("uses branded cover fallback instead of generic hero image", async () => {
    const fs = await import("node:fs/promises");
    const hero = await fs.readFile(
      new URL(
        "../components/sponsors/SponsorBrandProfileHero.tsx",
        import.meta.url,
      ),
      "utf8",
    );
    expect(hero).toMatch(/useCoverFallback/);
    expect(hero).not.toMatch(/Acme Events/);
    expect(hero).not.toMatch(/brand\.heroImage/);
  });
});

describe("admin sponsor moderation page", () => {
  it("renders admin sponsors list", async () => {
    const fs = await import("node:fs/promises");
    const src = await fs.readFile(
      new URL("../app/admin/sponsors/page.tsx", import.meta.url),
      "utf8",
    );
    expect(src).toMatch(/fetchAdminSponsors/);
    expect(src).toMatch(/admin\.sponsors\.view/);
  });
});

describe("sponsor saved page", () => {
  it("saved page renders list controls", async () => {
    const fs = await import("node:fs/promises");
    const src = await fs.readFile(
      new URL("../app/sponsor/saved/page.tsx", import.meta.url),
      "utf8",
    );
    expect(src).toMatch(/fetchSponsorSaved/);
    expect(src).toMatch(/item_type/);
  });
});

describe("sponsor campaigns pages", () => {
  it("campaign list and inquiry form integration exist", async () => {
    const fs = await import("node:fs/promises");
    const list = await fs.readFile(
      new URL("../app/sponsor/campaigns/page.tsx", import.meta.url),
      "utf8",
    );
    expect(list).toMatch(/fetchSponsorCampaigns/);
    const detail = await fs.readFile(
      new URL("../app/sponsor/campaigns/[id]/page.tsx", import.meta.url),
      "utf8",
    );
    expect(detail).toMatch(/SponsorCampaignRecommendations/);
    const form = await fs.readFile(
      new URL("../components/sponsors/SponsorInquiryForm.tsx", import.meta.url),
      "utf8",
    );
    expect(form).toMatch(/Link to campaign/);
    const saved = await fs.readFile(
      new URL("../app/sponsor/saved/page.tsx", import.meta.url),
      "utf8",
    );
    expect(saved).toMatch(/addSavedItemToCampaign/);
  });

  it("reports pages render dashboard", async () => {
    const fs = await import("node:fs/promises");
    const reports = await fs.readFile(
      new URL("../app/sponsor/reports/page.tsx", import.meta.url),
      "utf8",
    );
    expect(reports).toMatch(/fetchSponsorOverviewReport/);
    expect(reports).toMatch(/SponsorReportDashboard/);
  });
});

describe("sponsor team settings page", () => {
  it("team page and invite modal exist", async () => {
    const fs = await import("node:fs/promises");
    const team = await fs.readFile(
      new URL("../app/sponsor/settings/team/page.tsx", import.meta.url),
      "utf8",
    );
    expect(team).toMatch(/fetchSponsorTeam/);
    expect(team).toMatch(/SponsorTeamInviteModal/);
    const modal = await fs.readFile(
      new URL(
        "../components/sponsor/team/SponsorTeamInviteModal.tsx",
        import.meta.url,
      ),
      "utf8",
    );
    expect(modal).toMatch(/isValidEmail/);
    expect(modal).toMatch(/inviteSponsorTeamMember/);
  });
});
