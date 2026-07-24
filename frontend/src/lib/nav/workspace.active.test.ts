import { describe, expect, it } from "vitest";

import {
  isNavItemActive,
  resolveActiveNavItem,
  type NavItem,
} from "./workspace";

function item(href: string, label = "Item"): NavItem {
  return { href, label };
}

describe("isNavItemActive", () => {
  it("highlights exact overview only under homeHref", () => {
    expect(isNavItemActive("/dashboard", item("/dashboard"), "/dashboard")).toBe(
      true,
    );
    expect(
      isNavItemActive("/dashboard/tickets", item("/dashboard"), "/dashboard"),
    ).toBe(false);
  });

  it("highlights nested personal routes for section items", () => {
    expect(
      isNavItemActive(
        "/dashboard/tickets/abc",
        item("/dashboard/tickets"),
        "/dashboard",
      ),
    ).toBe(true);
  });

  it("highlights Connect aliases for /connect nav item", () => {
    const connect = item("/connect", "Connect");
    expect(isNavItemActive("/connect", connect, "/dashboard")).toBe(true);
    expect(isNavItemActive("/connect/requests", connect, "/dashboard")).toBe(
      true,
    );
    expect(
      isNavItemActive("/dashboard/connect", connect, "/dashboard"),
    ).toBe(true);
    expect(
      isNavItemActive("/dashboard/connect/settings", connect, "/dashboard"),
    ).toBe(true);
  });

  it("highlights Host overview without activating all /host/*", () => {
    expect(isNavItemActive("/host", item("/host"), "/host")).toBe(true);
    expect(isNavItemActive("/host/events", item("/host"), "/host")).toBe(false);
    expect(
      isNavItemActive("/host/events", item("/host/events"), "/host"),
    ).toBe(true);
  });

  it("highlights Admin Users on list and nested detail routes", () => {
    const users = item("/admin/users", "Users");
    const overview = item("/admin", "Overview");
    const siblings = [
      overview,
      users,
      item("/admin/hosts", "Hosts"),
      item("/admin/events", "Events"),
      item("/admin/events/review", "Event review"),
      item("/admin/settings/runtime", "Runtime overview"),
      item("/admin/settings/runtime/ai", "AI"),
    ];

    expect(isNavItemActive("/admin/users", users, "/admin", siblings)).toBe(
      true,
    );
    expect(
      isNavItemActive("/admin/users/abc-123", users, "/admin", siblings),
    ).toBe(true);
    expect(
      isNavItemActive(
        "/admin/users/abc-123/impersonation",
        users,
        "/admin",
        siblings,
      ),
    ).toBe(true);
    expect(
      isNavItemActive("/admin/users", overview, "/admin", siblings),
    ).toBe(false);
    expect(
      isNavItemActive("/admin/users/abc-123", overview, "/admin", siblings),
    ).toBe(false);
  });

  it("defers Runtime overview to distinct category siblings", () => {
    const runtime = item("/admin/settings/runtime", "Runtime overview");
    const ai = item("/admin/settings/runtime/ai", "AI");
    const payments = item(
      "/admin/settings/runtime/payments",
      "Payment integration",
    );
    const siblings = [runtime, ai, payments];
    expect(
      isNavItemActive("/admin/settings/runtime/ai", runtime, "/admin", siblings),
    ).toBe(false);
    expect(
      isNavItemActive("/admin/settings/runtime/ai", ai, "/admin", siblings),
    ).toBe(true);
    expect(
      isNavItemActive(
        "/admin/settings/runtime/payments",
        payments,
        "/admin",
        siblings,
      ),
    ).toBe(true);
    expect(
      isNavItemActive("/admin/settings/runtime", runtime, "/admin", siblings),
    ).toBe(true);
  });

  it("highlights Email for specialist and runtime email paths", () => {
    const email = item("/admin/email/settings", "Email");
    expect(isNavItemActive("/admin/email/settings", email, "/admin")).toBe(
      true,
    );
    expect(
      isNavItemActive("/admin/settings/runtime/email", email, "/admin"),
    ).toBe(true);
  });

  it("keeps finance Payments distinct from Payment integration", () => {
    const financePayments = item("/admin/payments", "Payments");
    const paymentIntegration = item(
      "/admin/settings/runtime/payments",
      "Payment integration",
    );
    const siblings = [financePayments, paymentIntegration];
    expect(
      resolveActiveNavItem(
        "/admin/settings/runtime/payments",
        siblings,
        "/admin",
      )?.label,
    ).toBe("Payment integration");
    expect(
      resolveActiveNavItem("/admin/payments", siblings, "/admin")?.label,
    ).toBe("Payments");
  });

  it("defers Notifications to Notification settings sibling", () => {
    const notifications = item("/admin/notifications", "Notifications");
    const settings = item(
      "/admin/notifications/settings",
      "Notification settings",
    );
    const siblings = [notifications, settings];
    expect(
      isNavItemActive(
        "/admin/notifications/settings",
        notifications,
        "/admin",
        siblings,
      ),
    ).toBe(false);
    expect(
      isNavItemActive(
        "/admin/notifications/settings",
        settings,
        "/admin",
        siblings,
      ),
    ).toBe(true);
    expect(
      isNavItemActive(
        "/admin/notifications/campaigns",
        notifications,
        "/admin",
        siblings,
      ),
    ).toBe(true);
  });
});

describe("resolveActiveNavItem", () => {
  it("resolves Users for admin user detail paths", () => {
    const items = [
      item("/admin", "Overview"),
      item("/admin/users", "Users"),
      item("/admin/hosts", "Hosts"),
      item("/admin/events", "Events"),
      item("/admin/events/review", "Event review"),
    ];
    expect(
      resolveActiveNavItem("/admin/users", items, "/admin")?.label,
    ).toBe("Users");
    expect(
      resolveActiveNavItem(
        "/admin/users/550e8400-e29b-41d4-a716-446655440000",
        items,
        "/admin",
      )?.label,
    ).toBe("Users");
    expect(
      resolveActiveNavItem("/admin/events/review", items, "/admin")?.label,
    ).toBe("Event review");
  });
});
