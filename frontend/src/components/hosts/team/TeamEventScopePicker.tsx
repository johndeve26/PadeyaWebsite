"use client";

import { Select } from "@/components/ui";
import { SCOPE_OPTIONS, type TeamScope } from "@/lib/host-team-roles";
import type { EventItem } from "@/lib/types/events";

type Props = {
  scope: TeamScope;
  onScopeChange: (scope: TeamScope) => void;
  eventIds: string[];
  onEventIdsChange: (ids: string[]) => void;
  events: EventItem[];
  disabled?: boolean;
  hint?: string;
};

export function TeamEventScopePicker({
  scope,
  onScopeChange,
  eventIds,
  onEventIdsChange,
  events,
  disabled,
  hint,
}: Props) {
  return (
    <div className="space-y-3">
      <Select
        label="Scope"
        value={scope}
        onChange={(e) => onScopeChange(e.target.value as TeamScope)}
        hint={
          hint ||
          SCOPE_OPTIONS.find((o) => o.value === scope)?.hint ||
          undefined
        }
        disabled={disabled}
      >
        {SCOPE_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </Select>

      {scope === "selected_events" ? (
        <fieldset className="space-y-2">
          <legend className="text-sm font-semibold text-foreground">
            Selected events
          </legend>
          <p className="text-xs text-muted-foreground">
            Desk access follows these events (and any event staff assignments).
          </p>
          {events.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No events yet — invite now and assign events later.
            </p>
          ) : (
            <div className="max-h-48 space-y-1.5 overflow-y-auto rounded-md border border-border p-3">
              {events.map((ev) => {
                const checked = eventIds.includes(ev.id);
                return (
                  <label
                    key={ev.id}
                    className="flex cursor-pointer items-center gap-2 text-sm text-foreground"
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-[var(--brand-green)]"
                      checked={checked}
                      disabled={disabled}
                      onChange={() =>
                        onEventIdsChange(
                          checked
                            ? eventIds.filter((id) => id !== ev.id)
                            : [...eventIds, ev.id],
                        )
                      }
                    />
                    <span className="truncate">{ev.title}</span>
                  </label>
                );
              })}
            </div>
          )}
        </fieldset>
      ) : null}
    </div>
  );
}
