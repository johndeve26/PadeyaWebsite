/** Lightweight copy + tab→mode mapping for Fan Connect suggestions UI. */
import { describe, expect, it } from "vitest";

import { suggestionCtaFromState } from "./fan-connect-suggestion-cta";

const TABS = [
  { id: "mixed", label: "Best matches" },
  { id: "near_me", label: "Near me" },
  { id: "same_event", label: "Same event" },
  { id: "connections_of_connections", label: "Friends of friends" },
  { id: "same_interests", label: "Same interests" },
  { id: "new_people", label: "New people" },
] as const;

function emptyCopy(mode: (typeof TABS)[number]["id"]) {
  switch (mode) {
    case "near_me":
      return "No nearby fans yet. Try widening your radius.";
    case "connections_of_connections":
      return "No friends-of-friends yet. Connect with more fans to improve this.";
    case "same_interests":
      return "Add interests to your Fan Passport to get better suggestions.";
    case "same_event":
      return "Get tickets to public nights on Pàdéyá to meet fans going too.";
    case "new_people":
      return "Check back soon — fresh Passports appear here as fans join.";
    default:
      return "Suggestions only show opted-in fans with shared event energy — never a dating feed.";
  }
}

function suggestionCta(state: string | undefined) {
  return suggestionCtaFromState(state);
}

describe("fan-connect suggestions UI mapping", () => {
  it("maps API cta_state to card CTA", () => {
    expect(suggestionCta("request_pending")).toBe("request_sent");
    expect(suggestionCta("message")).toBe("message");
    expect(suggestionCta("decline_cooldown")).toBe("decline_cooldown");
    expect(suggestionCta("connect")).toBe("connect");
    expect(suggestionCta(undefined)).toBe("connect");
  });

  it("maps tabs to API modes", () => {
    expect(TABS.map((t) => t.id)).toEqual([
      "mixed",
      "near_me",
      "same_event",
      "connections_of_connections",
      "same_interests",
      "new_people",
    ]);
  });

  it("has mode-specific empty copy", () => {
    expect(emptyCopy("near_me")).toContain("widening");
    expect(emptyCopy("connections_of_connections")).toContain("friends-of-friends");
    expect(emptyCopy("same_interests")).toContain("Fan Passport");
    expect(emptyCopy("same_event")).toContain("Pàdéyá");
    expect(emptyCopy("mixed")).toContain("dating feed");
  });

  it("never suggests showing exact GPS in reason copy helpers", () => {
    const safe = ["Nearby", "2.4 km away", "You’re both around Lagos"];
    for (const label of safe) {
      expect(label.toLowerCase()).not.toMatch(/latitude|longitude|gps/);
    }
  });
});
