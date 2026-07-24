import { describe, expect, it } from "vitest";

import type { User } from "../auth/types";
import { canSeeAdminNavItem, navForAdmin, navGroupsForAdmin } from "./admin-nav";

function user(partial: Partial<User> & Pick<User, "permissions" | "roles">): User {
  return {
    id: "1",
    email: "a@example.com",
    full_name: "Admin",
    is_active: true,
    is_verified: true,
    created_at: new Date().toISOString(),
    ...partial,
  };
}

describe("admin nav Users visibility", () => {
  it("shows Users for admin.users.view", () => {
    const u = user({
      roles: ["support_agent"],
      permissions: ["admin.users.view"],
    });
    expect(
      canSeeAdminNavItem(u, {
        href: "/admin/users",
        label: "Users",
        permissions: ["admin.users.view"],
      }),
    ).toBe(true);
    const platform = navGroupsForAdmin(u).find((g) => g.label === "Platform");
    expect(platform?.items.some((i) => i.href === "/admin/users")).toBe(true);
  });

  it("places Users immediately after Overview in Platform", () => {
    const u = user({
      roles: ["super_admin"],
      permissions: ["admin.full_access"],
    });
    const platform = navGroupsForAdmin(u).find((g) => g.label === "Platform");
    expect(platform?.items.map((i) => i.href).slice(0, 3)).toEqual([
      "/admin",
      "/admin/users",
      "/admin/hosts",
    ]);
  });

  it("includes Users in flat nav used by mobile drawer", () => {
    const u = user({
      roles: ["super_admin"],
      permissions: ["admin.full_access"],
    });
    expect(navForAdmin(u).some((i) => i.href === "/admin/users")).toBe(true);
  });

  it("does not show Users for users.read alone", () => {
    const u = user({
      roles: ["finance_admin"],
      permissions: ["users.read"],
    });
    expect(
      canSeeAdminNavItem(u, {
        href: "/admin/users",
        label: "Users",
        permissions: ["admin.users.view"],
      }),
    ).toBe(false);
  });

  it("shows Users for admin.full_access", () => {
    const u = user({
      roles: ["super_admin"],
      permissions: ["admin.full_access"],
    });
    expect(
      canSeeAdminNavItem(u, {
        href: "/admin/users",
        label: "Users",
        permissions: ["admin.users.view"],
      }),
    ).toBe(true);
  });

  it("hides Users without view permission", () => {
    const u = user({
      roles: ["support_agent"],
      permissions: ["support.reply"],
    });
    expect(
      canSeeAdminNavItem(u, {
        href: "/admin/users",
        label: "Users",
        permissions: ["admin.users.view"],
      }),
    ).toBe(false);
    const platform = navGroupsForAdmin(u).find((g) => g.label === "Platform");
    expect(platform?.items.some((i) => i.href === "/admin/users")).toBe(false);
  });
});

describe("admin nav Notification settings visibility", () => {
  it("shows Notification settings for manage_settings", () => {
    const u = user({
      roles: ["support_agent"],
      permissions: ["admin.notifications.manage_settings"],
    });
    const system = navGroupsForAdmin(u).find((g) => g.label === "System");
    expect(
      system?.items.some((i) => i.href === "/admin/notifications/settings"),
    ).toBe(true);
  });

  it("places Notification settings after Notifications in System", () => {
    const u = user({
      roles: ["super_admin"],
      permissions: ["admin.full_access"],
    });
    const system = navGroupsForAdmin(u).find((g) => g.label === "System");
    const hrefs = system?.items.map((i) => i.href) ?? [];
    const notificationsIdx = hrefs.indexOf("/admin/notifications");
    const settingsIdx = hrefs.indexOf("/admin/notifications/settings");
    expect(notificationsIdx).toBeGreaterThanOrEqual(0);
    expect(settingsIdx).toBe(notificationsIdx + 1);
  });
});
