"use client";

import {
  OWNER_ONLY_PERMISSION_KEYS,
  PERMISSION_GROUPS,
} from "@/lib/host-team-roles";
import type {
  HostTeamPermissionKey,
  HostTeamPermissions,
} from "@/lib/types/lifecycle";

type Props = {
  perms: HostTeamPermissions;
  onToggle: (key: HostTeamPermissionKey) => void;
  isOwner: boolean;
  disabled?: boolean;
  /** Limit groups — useful for scanner/merch focused forms. */
  groupTitles?: string[];
  compact?: boolean;
};

export function TeamPermissionToggles({
  perms,
  onToggle,
  isOwner,
  disabled,
  groupTitles,
  compact,
}: Props) {
  const groups = groupTitles
    ? PERMISSION_GROUPS.filter((g) => groupTitles.includes(g.title))
    : PERMISSION_GROUPS;

  return (
    <div
      className={
        compact
          ? "max-h-56 space-y-3 overflow-y-auto rounded-md border border-border p-3"
          : "space-y-4"
      }
    >
      {groups.map((group) => (
        <fieldset key={group.title} className="space-y-1.5">
          <legend className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
            {group.title}
          </legend>
          {group.hint ? (
            <p className="text-xs text-muted-foreground">{group.hint}</p>
          ) : null}
          {group.keys.map(({ key, label }) => {
            const locked =
              !isOwner && OWNER_ONLY_PERMISSION_KEYS.includes(key);
            return (
              <label
                key={key}
                className="flex cursor-pointer items-center gap-2 text-sm text-foreground"
              >
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-[var(--brand-green)]"
                  checked={Boolean(perms[key])}
                  disabled={disabled || locked}
                  onChange={() => onToggle(key)}
                />
                <span>
                  {label}
                  {locked ? " (owner only)" : ""}
                </span>
              </label>
            );
          })}
        </fieldset>
      ))}
    </div>
  );
}
