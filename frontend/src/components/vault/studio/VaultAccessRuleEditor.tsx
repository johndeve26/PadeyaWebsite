"use client";

import { useMemo } from "react";

import { Input, Select } from "@/components/ui";
import type { EventItem } from "@/lib/types/events";
import {
  ACCESS_TYPE_HINTS,
  ACCESS_TYPES,
  type VaultAccessDraft,
} from "@/lib/types/vault";

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

type Props = {
  value: VaultAccessDraft;
  onChange: (next: VaultAccessDraft) => void;
  events: EventItem[];
};

function needsEventScope(accessType: string) {
  return (
    accessType === "ticket_holder_only" ||
    accessType === "checked_in_attendee_only" ||
    accessType === "vip_ticket_holder_only"
  );
}

export function VaultAccessRuleEditor({ value, onChange, events }: Props) {
  const selectedEvent = useMemo(
    () => events.find((e) => e.id === value.required_event_id) ?? null,
    [events, value.required_event_id],
  );
  const ticketTypes = selectedEvent?.ticket_types ?? [];
  const scoped = needsEventScope(value.access_type);
  const needsPrice = value.access_type === "one_time_unlock";
  const needsInviteCode = value.access_type === "invite_only";

  return (
    <div className="space-y-4">
      <Select
        label="Access type"
        value={value.access_type}
        onChange={(e) => {
          const nextType = e.target.value;
          onChange({
            ...value,
            access_type: nextType,
            required_event_id: needsEventScope(nextType)
              ? value.required_event_id
              : "",
            required_ticket_type_id: needsEventScope(nextType)
              ? value.required_ticket_type_id
              : "",
            require_check_in:
              nextType === "checked_in_attendee_only"
                ? true
                : needsEventScope(nextType)
                  ? value.require_check_in
                  : false,
            access_code: nextType === "invite_only" ? value.access_code : "",
          });
        }}
        hint={ACCESS_TYPE_HINTS[value.access_type] || "Who can unlock this drop."}
      >
        {ACCESS_TYPES.map((t) => (
          <option key={t} value={t}>
            {formatLabel(t)}
          </option>
        ))}
      </Select>

      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Price"
          type="number"
          min="0"
          step="0.01"
          value={value.price}
          onChange={(e) => onChange({ ...value, price: e.target.value })}
          hint={
            needsPrice
              ? "Required for one-time unlock — charged at secure checkout."
              : "Stored on the access rule (usually 0)."
          }
          required={needsPrice}
        />
        <Select
          label="Currency"
          value={value.currency}
          onChange={(e) => onChange({ ...value, currency: e.target.value })}
        >
          <option value="NGN">NGN</option>
          <option value="USD">USD</option>
          <option value="GBP">GBP</option>
        </Select>
      </div>

      {scoped ? (
        <>
          <Select
            label="Required event (optional)"
            value={value.required_event_id}
            onChange={(e) =>
              onChange({
                ...value,
                required_event_id: e.target.value,
                required_ticket_type_id: "",
              })
            }
            hint="Limit access to tickets for a specific event. Falls back to the item’s related event when empty."
          >
            <option value="">Any host event ticket</option>
            {events.map((event) => (
              <option key={event.id} value={event.id}>
                {event.title}
              </option>
            ))}
          </Select>

          {ticketTypes.length > 0 ? (
            <Select
              label="Required ticket type (optional)"
              value={value.required_ticket_type_id}
              onChange={(e) =>
                onChange({ ...value, required_ticket_type_id: e.target.value })
              }
              hint={
                value.access_type === "vip_ticket_holder_only"
                  ? "Optional. Leave empty to accept any VIP/VVIP type."
                  : "Optional. Leave empty to accept any ticket type."
              }
            >
              <option value="">Any matching ticket type</option>
              {ticketTypes.map((tt) => (
                <option key={tt.id} value={tt.id}>
                  {tt.name} ({tt.type})
                </option>
              ))}
            </Select>
          ) : null}

          {value.access_type !== "checked_in_attendee_only" ? (
            <label className="flex items-start gap-3 rounded-[var(--radius-md)] border border-border bg-muted/50 px-4 py-3 text-sm">
              <input
                type="checkbox"
                className="mt-0.5 accent-accent"
                checked={value.require_check_in}
                onChange={(e) =>
                  onChange({ ...value, require_check_in: e.target.checked })
                }
              />
              <span>
                <span className="font-semibold text-foreground">
                  Also require verified check-in
                </span>
                <span className="mt-0.5 block text-muted-foreground">
                  For ticket-holder rules, optionally require QR check-in. Prefer
                  checked-in attendee access type when check-in is mandatory.
                </span>
              </span>
            </label>
          ) : (
            <p className="text-sm text-muted-foreground">
              Checked-in attendee access always requires a checked-in ticket.
            </p>
          )}
        </>
      ) : null}

      {needsInviteCode ? (
        <Input
          label="Access code"
          value={value.access_code}
          onChange={(e) => onChange({ ...value, access_code: e.target.value })}
          hint="Stored hashed — never returned by the API. Enter a new code to rotate. Required before publishing invite-only drops."
          placeholder="Set or rotate invite code"
          autoComplete="off"
        />
      ) : null}

      <Input
        label="Required Legacy tier (placeholder)"
        value={value.required_legacy_tier}
        onChange={(e) =>
          onChange({ ...value, required_legacy_tier: e.target.value })
        }
        hint="Stored for future tier gates — not enforced yet."
        placeholder="e.g. gold"
      />

      <Input
        label="Max unlocks (optional)"
        type="number"
        min="1"
        step="1"
        value={value.max_unlocks}
        onChange={(e) => onChange({ ...value, max_unlocks: e.target.value })}
        hint="Cap paid/invite/manual grants. Leave empty for unlimited."
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Access starts at (optional)"
          type="datetime-local"
          value={value.starts_at}
          onChange={(e) => onChange({ ...value, starts_at: e.target.value })}
        />
        <Input
          label="Access ends at (optional)"
          type="datetime-local"
          value={value.ends_at}
          onChange={(e) => onChange({ ...value, ends_at: e.target.value })}
        />
      </div>
    </div>
  );
}
