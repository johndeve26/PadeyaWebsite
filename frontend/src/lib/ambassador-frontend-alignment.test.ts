import { describe, expect, it } from "vitest";

import {
  assertNoSingleWinnerWording,
  DUAL_COMMISSION_COPY,
  enrollmentScopeAnalytics,
  resolveOwnPlatformLinkPath,
  resolvePublicEnrollmentState,
  adminEnrollmentScopeLabel,
  overviewArrangementHint,
  overviewCommissionHint,
  platformWideCoverageCopy,
  hostCampaignCoverageCopy,
} from "@/lib/ambassador-frontend-alignment";

describe("ambassador frontend alignment helpers", () => {
  it("labels platform enrollments correctly", () => {
    expect(adminEnrollmentScopeLabel("platform_wide")).toBe("Pàdéyá-wide");
    expect(adminEnrollmentScopeLabel("open_event")).toBe("Host campaign");
    expect(adminEnrollmentScopeLabel("host_curated")).toBe("Host campaign");
  });

  it("states platform-wide needs no host opt-in", () => {
    expect(platformWideCoverageCopy()).toMatch(/no host opt-in/i);
    expect(hostCampaignCoverageCopy()).toMatch(/host enables/i);
  });

  it("formats overview arrangement and commission hints", () => {
    expect(overviewArrangementHint(4, 8)).toBe(
      "4 Pàdéyá programs · 8 host campaigns",
    );
    expect(overviewCommissionHint("₦150,000", "₦90,000")).toContain(
      "host-funded",
    );
    expect(overviewCommissionHint("₦150,000", "₦90,000")).toContain(
      "Pàdéyá-funded",
    );
  });

  it("resolves public CTA enrollment states", () => {
    expect(resolvePublicEnrollmentState(false, false, null, [])).toBe(
      "signed_out",
    );
    expect(resolvePublicEnrollmentState(true, true, null, [])).toBe("loading");
    expect(
      resolvePublicEnrollmentState(true, false, { enrollments_active: 0 }, []),
    ).toBe("not_enrolled");
    expect(
      resolvePublicEnrollmentState(
        true,
        false,
        {
          enrollments_active: 1,
          has_platform_enrollment: true,
          has_host_enrollment: false,
        },
        [{ status: "active", scope: "platform", scope_badge: "Platform" }],
      ),
    ).toBe("platform_only");
    expect(
      resolvePublicEnrollmentState(
        true,
        false,
        {
          enrollments_active: 1,
          has_platform_enrollment: false,
          has_host_enrollment: true,
        },
        [{ status: "active", scope: "event", scope_badge: "Host" }],
      ),
    ).toBe("host_only");
    expect(
      resolvePublicEnrollmentState(
        true,
        false,
        {
          enrollments_active: 2,
          has_platform_enrollment: true,
          has_host_enrollment: true,
        },
        [
          { status: "active", scope: "platform", scope_badge: "Platform" },
          { status: "active", scope: "event", scope_badge: "Host" },
        ],
      ),
    ).toBe("both");
    expect(
      resolvePublicEnrollmentState(
        true,
        false,
        { enrollments_active: 1, has_platform_enrollment: true },
        [{ status: "ended", scope: "platform", scope_badge: "Platform" }],
      ),
    ).toBe("inactive");
    // Personalization failure → safe not_enrolled (no fabricated link)
    expect(resolvePublicEnrollmentState(true, false, null, [])).toBe(
      "not_enrolled",
    );
  });

  it("uses backend-provided platform link only", () => {
    expect(resolveOwnPlatformLinkPath(null, [])).toBeNull();
    expect(
      resolveOwnPlatformLinkPath(
        { enrollments_active: 1, primary_referral_link_path: "/r/ada" },
        [],
      ),
    ).toBe("/r/ada");
    expect(
      resolveOwnPlatformLinkPath(
        { enrollments_active: 1, has_platform_enrollment: true },
        [
          {
            status: "active",
            scope: "platform",
            scope_badge: "Platform",
            referral_link_path: "/r/tolu",
          },
        ],
      ),
    ).toBe("/r/tolu");
    expect(
      resolveOwnPlatformLinkPath(
        { enrollments_active: 1, has_host_enrollment: true },
        [
          {
            status: "active",
            scope: "event",
            referral_link_path: "/events/x?ref=host1",
          },
        ],
      ),
    ).toBeNull();
  });

  it("maps enrollment scope for analytics", () => {
    expect(enrollmentScopeAnalytics("both")).toBe("both");
    expect(enrollmentScopeAnalytics("not_enrolled")).toBe("none");
    expect(enrollmentScopeAnalytics("platform_only")).toBe("platform");
  });

  it("dual-commission copy avoids single-winner wording", () => {
    const blob = Object.values(DUAL_COMMISSION_COPY).join("\n");
    expect(assertNoSingleWinnerWording(blob)).toBe(true);
    expect(assertNoSingleWinnerWording("host campaign wins for that item")).toBe(
      false,
    );
    expect(DUAL_COMMISSION_COPY.settlementNote).toMatch(/does not reduce/i);
    expect(DUAL_COMMISSION_COPY.hostEnrollmentRequired).toMatch(/must be enrolled/i);
    expect(DUAL_COMMISSION_COPY.usernameExample).toContain("/r/");
  });
});
