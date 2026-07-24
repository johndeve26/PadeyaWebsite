"use client";

import { Input, Select } from "@/components/ui";

/** Canonical Event Studio ticket kinds (matches backend presets). */
export const STUDIO_TICKET_TYPES = [
  { value: "regular", label: "Regular" },
  { value: "early_bird", label: "Early bird" },
  { value: "vip", label: "VIP" },
  { value: "vvip", label: "VVIP" },
  { value: "table", label: "Table" },
  { value: "group", label: "Group" },
  { value: "free_rsvp", label: "Free RSVP" },
  { value: "invite_only", label: "Invite only" },
  { value: "hidden", label: "Hidden" },
  { value: "donation", label: "Donation" },
] as const;

export const PRESET_TICKET_KINDS = STUDIO_TICKET_TYPES.map((t) => t.value);

const CUSTOM_VALUE = "__custom__";

function isPreset(value: string): boolean {
  return (PRESET_TICKET_KINDS as readonly string[]).includes(value);
}

/** Normalize host-entered custom kinds to API-safe slugs. */
export function normalizeTicketKind(value: string): string {
  const cleaned = value
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_")
    .replace(/[^a-z0-9_-]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^[_-]+|[_-]+$/g, "")
    .slice(0, 32);
  // Legacy alias
  if (cleaned === "free") return "free_rsvp";
  return cleaned;
}

export function TicketKindField({
  value,
  onChange,
  disabled = false,
}: {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  const normalized = value === "free" ? "free_rsvp" : value;
  const customMode = !isPreset(normalized);
  const selectValue = customMode ? CUSTOM_VALUE : normalized || "regular";

  return (
    <div className="space-y-3">
      <Select
        label="Type"
        hint="Ticket kind — tables and groups can cover multiple seats per unit."
        value={selectValue}
        disabled={disabled}
        onChange={(e) => {
          const next = e.target.value;
          if (next === CUSTOM_VALUE) {
            onChange("");
            return;
          }
          onChange(next);
        }}
      >
        {STUDIO_TICKET_TYPES.map((kind) => (
          <option key={kind.value} value={kind.value}>
            {kind.label}
          </option>
        ))}
        <option value={CUSTOM_VALUE}>Custom…</option>
      </Select>
      {customMode && !disabled ? (
        <Input
          label="Custom type"
          required
          hint="Letters and numbers — saved as a short slug (e.g. backstage_pass)"
          placeholder="e.g. Backstage Pass"
          value={value}
          onChange={(e) => onChange(normalizeTicketKind(e.target.value))}
          maxLength={32}
        />
      ) : null}
    </div>
  );
}
