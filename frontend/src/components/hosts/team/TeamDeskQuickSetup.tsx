"use client";

import { Button } from "@/components/ui";
import {
  mergePermissions,
  permissionsForRole,
  type TeamScope,
} from "@/lib/host-team-roles";
import type { HostTeamPermissions } from "@/lib/types/lifecycle";

export type DeskQuickKind = "scanner" | "merch_staff";

type Props = {
  role: string;
  scope: TeamScope;
  perms: HostTeamPermissions;
  onApply: (next: {
    role: DeskQuickKind;
    scope: TeamScope;
    perms: HostTeamPermissions;
  }) => void;
  disabled?: boolean;
};

/**
 * One-tap presets for door scanners and merch pickup staff.
 * Defaults to selected-events scope (hybrid desk) without host-wide scan keys.
 */
export function TeamDeskQuickSetup({
  role,
  scope,
  perms,
  onApply,
  disabled,
}: Props) {
  function apply(kind: DeskQuickKind) {
    onApply({
      role: kind,
      scope: "selected_events",
      perms: permissionsForRole(kind),
    });
  }

  function enableHostWideDesk(kind: DeskQuickKind) {
    const base = mergePermissions(permissionsForRole(kind));
    if (kind === "scanner") {
      base["tickets.scan_qr"] = true;
      base["tickets.check_in"] = true;
    } else {
      base["merch.scan_pickup_qr"] = true;
      base["merch.mark_picked_up"] = true;
    }
    onApply({ role: kind, scope: "host_wide", perms: base });
  }

  const scannerActive = role === "scanner";
  const merchActive = role === "merch_staff";
  const hostWideDesk =
    scope === "host_wide" &&
    ((scannerActive &&
      (perms["tickets.scan_qr"] || perms["tickets.check_in"])) ||
      (merchActive &&
        (perms["merch.scan_pickup_qr"] || perms["merch.mark_picked_up"])));

  return (
    <div className="space-y-3 rounded-md border border-border bg-surface-muted p-3">
      <div>
        <p className="text-sm font-semibold text-foreground">
          Quick desk setup
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Scanner and merch staff work best on selected events. Host-wide desk
          is optional for trusted leads.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant={scannerActive && !hostWideDesk ? "primary" : "secondary"}
          disabled={disabled}
          onClick={() => apply("scanner")}
        >
          Scanner · selected events
        </Button>
        <Button
          type="button"
          size="sm"
          variant={merchActive && !hostWideDesk ? "primary" : "secondary"}
          disabled={disabled}
          onClick={() => apply("merch_staff")}
        >
          Merch · selected events
        </Button>
        <Button
          type="button"
          size="sm"
          variant={
            scannerActive && hostWideDesk ? "primary" : "secondary"
          }
          disabled={disabled}
          onClick={() => enableHostWideDesk("scanner")}
        >
          Scanner · all events
        </Button>
        <Button
          type="button"
          size="sm"
          variant={merchActive && hostWideDesk ? "primary" : "secondary"}
          disabled={disabled}
          onClick={() => enableHostWideDesk("merch_staff")}
        >
          Merch · all events
        </Button>
      </div>
    </div>
  );
}
