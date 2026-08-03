import { describe, expect, it } from "vitest";

import {
  adminEnrollmentScopeLabel,
  overviewArrangementHint,
  overviewCommissionHint,
  resolvePublicEnrollmentState,
} from "@/lib/ambassador-frontend-alignment";

describe("ambassador frontend alignment helpers", () => {
  it("labels platform enrollments correctly", () => {
    expect(adminEnrollmentScopeLabel("platform_wide")).toBe("Pàdéyá-wide");
    expect(adminEnrollmentScopeLabel("open_event")).toBe("Host campaign");
    expect(adminEnrollmentScopeLabel("host_curated")).toBe("Host campaign");
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
  });
});
