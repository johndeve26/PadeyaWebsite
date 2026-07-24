"use client";

import { cn } from "@/lib/cn";
import { Input, Select, Textarea } from "@/components/ui";

import { StudioFieldGroup, StudioMicrocopy } from "./studio-ui";

export const LOCATION_VISIBILITY_OPTIONS = [
  {
    value: "full_public",
    label: "Exact public",
    help: "Fans can see the venue address and exact map pin before buying.",
  },
  {
    value: "area_only",
    label: "Approximate area only",
    help: "Fans see the area, not the exact street address.",
  },
  {
    value: "hidden_until_payment",
    label: "Hidden until ticket purchase",
    help: "Fans see the city/area before payment. Confirmed ticket holders see the exact venue.",
  },
  {
    value: "online_only",
    label: "Online / no physical venue",
    help: "No physical map pin needed.",
  },
  {
    value: "hidden_until_24h_before",
    label: "Hidden until 24h before",
    help: "Exact address stays hidden on public pages; reveal opens ~24 hours before start (and for eligible buyers).",
  },
  {
    value: "hidden_until_manual_approval",
    label: "Hidden until manual approval",
    help: "Secret location — full details only for approved / allowed attendees.",
  },
] as const;

export const PRIMARY_LOCATION_VISIBILITY = [
  "full_public",
  "area_only",
  "hidden_until_payment",
  "online_only",
] as const;

export const REVEAL_TIMING_OPTIONS = [
  {
    value: "immediately",
    label: "Immediately",
    help: "Eligible viewers can see the restricted detail as soon as they qualify.",
  },
  {
    value: "after_payment",
    label: "After payment",
    help: "Ticket holders with a confirmed purchase get the detail after payment.",
  },
  {
    value: "twenty_four_hours_before",
    label: "24 hours before",
    help: "Reveal opens twenty-four hours before event start.",
  },
  {
    value: "manual_approval",
    label: "Manual approval",
    help: "Reveal only after you approve the guest (or equivalent access).",
  },
  {
    value: "event_day",
    label: "Event day",
    help: "Reveal opens on the calendar day of the event.",
  },
] as const;

function defaultRevealForVisibility(visibility: string): string {
  if (visibility === "full_public") return "immediately";
  if (visibility === "hidden_until_24h_before") return "twenty_four_hours_before";
  if (visibility === "hidden_until_manual_approval") return "manual_approval";
  if (visibility === "online_only") return "after_payment";
  return "after_payment";
}

export function LocationPrivacySelector({
  values,
  onChange,
}: {
  values: {
    location_visibility: string;
    reveal_timing: string;
    reveal_note: string;
    online_event_url: string;
    online_url_reveal_rule: string;
  };
  onChange: (key: string, value: string) => void;
}) {
  const revealHelp =
    REVEAL_TIMING_OPTIONS.find((o) => o.value === values.reveal_timing)?.help ||
    "When ticket holders get the exact address.";
  const onlineRevealHelp =
    REVEAL_TIMING_OPTIONS.find((o) => o.value === values.online_url_reveal_rule)
      ?.help || "When buyers receive the join link.";

  const moreModes = LOCATION_VISIBILITY_OPTIONS.filter(
    (o) => !PRIMARY_LOCATION_VISIBILITY.includes(o.value as (typeof PRIMARY_LOCATION_VISIBILITY)[number]),
  );

  return (
    <div className="space-y-4">
      <StudioFieldGroup
        title="Location visibility"
        description="Choose what fans see before they buy. Hosts and admins always keep the full private address."
      >
        <div className="grid gap-3 sm:grid-cols-2">
          {LOCATION_VISIBILITY_OPTIONS.filter((o) =>
            PRIMARY_LOCATION_VISIBILITY.includes(o.value as (typeof PRIMARY_LOCATION_VISIBILITY)[number]),
          ).map((opt) => {
            const selected = values.location_visibility === opt.value;
            return (
              <label
                key={opt.value}
                className={cn(
                  "flex cursor-pointer flex-col gap-1 rounded-[var(--radius-lg)] border p-4 transition-colors",
                  selected
                    ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                    : "border-border bg-card/50 hover:border-border-strong dark:bg-surface-elevated/50",
                )}
              >
                <span className="flex items-start gap-2">
                  <input
                    type="radio"
                    name="location_visibility"
                    className="mt-1"
                    checked={selected}
                    onChange={() => {
                      onChange("location_visibility", opt.value);
                      onChange("reveal_timing", defaultRevealForVisibility(opt.value));
                    }}
                  />
                  <span className="text-sm font-semibold text-foreground">{opt.label}</span>
                </span>
                <span className="pl-6 text-xs leading-relaxed text-muted-foreground">
                  {opt.help}
                </span>
              </label>
            );
          })}
        </div>

        <details className="rounded-[var(--radius-md)] border border-border px-3 py-2">
          <summary className="cursor-pointer text-xs font-semibold text-muted-foreground">
            More visibility options
          </summary>
          <div className="mt-3 space-y-2">
            {moreModes.map((opt) => (
              <label key={opt.value} className="flex items-start gap-2 text-sm">
                <input
                  type="radio"
                  name="location_visibility_more"
                  checked={values.location_visibility === opt.value}
                  onChange={() => {
                    onChange("location_visibility", opt.value);
                    onChange("reveal_timing", defaultRevealForVisibility(opt.value));
                  }}
                />
                <span>
                  <span className="font-semibold text-foreground">{opt.label}</span>
                  <span className="mt-0.5 block text-xs text-muted-foreground">{opt.help}</span>
                </span>
              </label>
            ))}
          </div>
        </details>

        <Select
          label="Reveal timing"
          hint={revealHelp}
          value={values.reveal_timing}
          onChange={(e) => onChange("reveal_timing", e.target.value)}
        >
          {REVEAL_TIMING_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Textarea
          label="Note on public page"
          rows={2}
          hint="Short reassurance under the location when the address is hidden."
          value={values.reveal_note}
          onChange={(e) => onChange("reveal_note", e.target.value)}
          placeholder="Exact venue revealed after purchase."
        />
      </StudioFieldGroup>

      <StudioFieldGroup
        title="Online access"
        description="Join links stay private until your reveal rule says otherwise."
      >
        <Input
          label="Online event URL"
          hint="Zoom, Meet, or livestream — hosts always see it; guests follow the rule below."
          value={values.online_event_url}
          onChange={(e) => onChange("online_event_url", e.target.value)}
          placeholder="https://"
        />
        <Select
          label="Online URL reveal rule"
          hint={onlineRevealHelp}
          value={values.online_url_reveal_rule}
          onChange={(e) => onChange("online_url_reveal_rule", e.target.value)}
        >
          {REVEAL_TIMING_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
      </StudioFieldGroup>

      <div className="rounded-[var(--radius-md)] border border-accent/30 bg-[color-mix(in_srgb,var(--brand-green)_8%,transparent)] px-4 py-3">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Guest experience
        </p>
        <StudioMicrocopy>
          {LOCATION_VISIBILITY_OPTIONS.find((o) => o.value === values.location_visibility)
            ?.help ||
            "Controls how much of the venue guests see before they buy."}
        </StudioMicrocopy>
      </div>
    </div>
  );
}
