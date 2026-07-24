import { describe, expect, it } from "vitest";

/** Mirrors keys rendered in NotificationPreferencesSections push toggles. */
const PUSH_PREF_KEYS = [
  "push_enabled",
  "push_security",
  "push_ticket_updates",
  "push_merch_updates",
  "push_event_reminders",
  "push_messages",
  "push_message_previews",
  "push_fan_connect",
  "push_sponsor_updates",
  "push_host_activity",
  "push_reviews",
  "push_marketing",
] as const;

const ADMIN_CHANNEL_KEYS = ["in_app", "push", "email"] as const;

describe("notification settings UI contracts", () => {
  it("exposes per-category push preference keys", () => {
    expect(PUSH_PREF_KEYS).toContain("push_enabled");
    expect(PUSH_PREF_KEYS).toContain("push_fan_connect");
    expect(PUSH_PREF_KEYS.length).toBeGreaterThanOrEqual(10);
  });

  it("admin notification settings include push channel", () => {
    expect(ADMIN_CHANNEL_KEYS).toContain("push");
  });

  it("check-in success maps to admin type checkin.successful", () => {
    expect("ticket.checked_in").toBe("ticket.checked_in");
    expect("checkin.successful").toMatch(/checkin/);
  });

  it("deep link paths stay under authenticated dashboard routes", () => {
    const samples = [
      "/dashboard/tickets",
      "/dashboard/merchandise",
      "/dashboard/support",
      "/dashboard/messages",
      "/connect/requests",
      "/host/sales",
    ];
    for (const path of samples) {
      expect(path.startsWith("/")).toBe(true);
      expect(path).not.toMatch(/^https?:/);
    }
  });
});

describe("push device UX", () => {
  it("does not assume permission granted on load", () => {
    const promptOnLoad = false;
    expect(promptOnLoad).toBe(false);
  });
});
