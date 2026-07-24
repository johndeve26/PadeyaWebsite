import { describe, expect, it } from "vitest";

import {
  hostHomePathForWorkspace,
  workspaceManagementHint,
  workspaceSwitcherOptionLabel,
} from "./host-access";
import type { HostWorkspace } from "./types/host-workspace";
import type { HostTeamPermissions } from "./types/lifecycle";

function perms(
  grants: Partial<HostTeamPermissions> = {},
): HostTeamPermissions {
  return grants as HostTeamPermissions;
}

function workspace(
  partial: Partial<HostWorkspace> &
    Pick<HostWorkspace, "role" | "is_owner"> & {
      permissions?: Partial<HostTeamPermissions>;
    },
): HostWorkspace {
  return {
    host_id: "h1",
    display_name: "Test Host",
    slug: "test-host",
    kind: partial.is_owner ? "owner" : "team_member",
    role_label: partial.role,
    scope: "host_wide",
    scoped_event_ids: [],
    membership_id: partial.is_owner ? null : "m1",
    ...partial,
    permissions: perms(partial.permissions),
  };
}

describe("hostHomePathForWorkspace", () => {
  it("sends host owners to /host", () => {
    expect(
      hostHomePathForWorkspace(workspace({ role: "owner", is_owner: true })),
    ).toBe("/host");
  });

  it("sends desk-focused scanner staff to /host/desk", () => {
    expect(
      hostHomePathForWorkspace(
        workspace({
          role: "scanner",
          is_owner: false,
          permissions: { "tickets.scan_qr": true },
        }),
      ),
    ).toBe("/host/desk");
  });

  it("sends desk-focused merch staff to /host/desk", () => {
    expect(
      hostHomePathForWorkspace(
        workspace({
          role: "merch_staff",
          is_owner: false,
          permissions: { "merch.scan_pickup_qr": true },
        }),
      ),
    ).toBe("/host/desk");
  });

  it("sends sponsor managers with grants to /host/sponsorships", () => {
    expect(
      hostHomePathForWorkspace(
        workspace({
          role: "sponsor_manager",
          is_owner: false,
          permissions: { "sponsors.view": true },
        }),
      ),
    ).toBe("/host/sponsorships");
  });

  it("sends sponsor-desk-only host team to /host/sponsorships", () => {
    expect(
      hostHomePathForWorkspace(
        workspace({
          role: "viewer",
          is_owner: false,
          role_label: "Sponsor Observer",
          permissions: {
            "sponsors.view": true,
            "analytics.view_sponsors": true,
          },
        }),
      ),
    ).toBe("/host/sponsorships");
  });

  it("sends viewers to /host (read-only overview)", () => {
    expect(
      hostHomePathForWorkspace(
        workspace({
          role: "viewer",
          is_owner: false,
          permissions: { "events.view": true },
        }),
      ),
    ).toBe("/host");
  });

  it("sends event managers to /host (existing helper default)", () => {
    expect(
      hostHomePathForWorkspace(
        workspace({
          role: "event_manager",
          is_owner: false,
          permissions: {
            "events.view": true,
            "events.edit": true,
            "events.create": true,
          },
        }),
      ),
    ).toBe("/host");
  });

  it("formats switcher options as Host: name with Owner/role suffixes", () => {
    expect(
      workspaceSwitcherOptionLabel(
        workspace({
          role: "owner",
          is_owner: true,
          display_name: "DJ Maze",
          role_label: "Owner",
        }),
      ),
    ).toBe("Host: DJ Maze (Owner)");
    expect(
      workspaceSwitcherOptionLabel(
        workspace({
          role: "scanner",
          is_owner: false,
          display_name: "DJ Maze",
          role_label: "Scanner",
          permissions: { "tickets.scan_qr": true },
        }),
      ),
    ).toBe("Host: DJ Maze · Scanner");
    expect(
      workspaceSwitcherOptionLabel(
        workspace({
          role: "viewer",
          is_owner: false,
          display_name: "DJ Maze",
          role_label: "",
          permissions: { "events.view": true },
        }),
      ),
    ).toBe("Host: DJ Maze");
  });

  it("never returns /host/events as a universal landing", () => {
    const roles = [
      workspace({ role: "owner", is_owner: true }),
      workspace({
        role: "scanner",
        is_owner: false,
        permissions: { "tickets.scan_qr": true },
      }),
      workspace({
        role: "merch_staff",
        is_owner: false,
        permissions: { "merch.mark_picked_up": true },
      }),
      workspace({
        role: "sponsor_manager",
        is_owner: false,
        permissions: { "sponsors.manage_slots": true },
      }),
      workspace({
        role: "viewer",
        is_owner: false,
        permissions: { "events.view": true },
      }),
      workspace({
        role: "event_manager",
        is_owner: false,
        permissions: { "events.edit": true },
      }),
      workspace({
        role: "admin",
        is_owner: false,
        permissions: { "team.invite": true, "events.edit": true },
      }),
    ];
    for (const row of roles) {
      expect(hostHomePathForWorkspace(row)).not.toBe("/host/events");
    }
  });
});

describe("workspaceManagementHint", () => {
  it("describes personal account", () => {
    expect(workspaceManagementHint({ surface: "personal" })).toBe(
      "You're managing your personal account.",
    );
  });

  it("describes host workspace by display name", () => {
    expect(
      workspaceManagementHint({
        surface: "host",
        hostDisplayName: "Ayo",
      }),
    ).toContain("Ayo");
    expect(
      workspaceManagementHint({
        surface: "host",
        hostDisplayName: "Ayo",
      }),
    ).toContain("workspace");
  });
});
