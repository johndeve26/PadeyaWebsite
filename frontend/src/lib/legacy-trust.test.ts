import { describe, expect, it } from "vitest";

import {
  legacyScoreAriaLabel,
  nextTierProgressCopy,
  provisionalReasonLabel,
} from "@/lib/legacy-trust";
import type { LegacyNextTierSummary, LegacyTrustSummary } from "@/lib/types/legacy";

describe("legacy-trust presentation", () => {
  it("builds accessible score labels", () => {
    expect(
      legacyScoreAriaLabel({
        displayScore: 72,
        tierName: "Icon",
        provisional: false,
      }),
    ).toContain("Legacy Score: 72 out of 100");
  });

  it("explains score-met gate-blocked next tier", () => {
    const next: LegacyNextTierSummary = {
      key: "icon",
      name: "Icon",
      min_score: 70,
      score_remaining: 0,
      score_requirement_met: true,
      gates_met: 2,
      gates_total: 5,
      gates_remaining: 3,
      state: "score_met_gates_remaining",
      unmet_requirements: [],
    };
    const copy = nextTierProgressCopy(next);
    expect(copy?.title).toBe("Score requirement met");
    expect(copy?.body).toContain("Icon range");
    expect(copy?.body).not.toContain("points to");
  });

  it("shows points remaining when score gate unmet", () => {
    const next: LegacyNextTierSummary = {
      key: "legend",
      name: "Legend",
      min_score: 85,
      score_remaining: 12.5,
      score_requirement_met: false,
      gates_met: 1,
      gates_total: 5,
      gates_remaining: 4,
      state: "in_progress",
      unmet_requirements: [],
    };
    const copy = nextTierProgressCopy(next);
    expect(copy?.title).toContain("points to Legend");
  });

  it("maps provisional reason codes to friendly copy", () => {
    expect(provisionalReasonLabel("limited_completed_events")).toContain(
      "completed events",
    );
  });

  it("keeps whole-number display_score from API trust payload", () => {
    const trust: LegacyTrustSummary = {
      score: 72.46,
      display_score: 72,
      tier: { key: "certified", name: "Certified" },
      legacy_status: "Certified",
      is_provisional: false,
      provisional_reasons: [],
      headline: "Trusted and consistently verified",
      evidence: [
        {
          key: "verified_rating",
          label: "Verified rating",
          value: 4.8,
          display: "4.8",
        },
      ],
      factor_bands: [],
    };
    expect(trust.display_score).toBe(72);
    expect(trust.display_score).not.toBe(trust.score);
  });
});
