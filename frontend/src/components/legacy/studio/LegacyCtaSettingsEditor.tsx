"use client";

import { Input, Select, Textarea } from "@/components/ui";

export type LegacyCtaDraft = {
  primaryLabel: string;
  primaryType: string;
  primaryValue: string;
  secondaryLabel: string;
  secondaryType: string;
  secondaryValue: string;
  sponsorshipAvailable: boolean;
  sponsorshipNote: string;
};

type Props = {
  value: LegacyCtaDraft;
  onChange: (next: LegacyCtaDraft) => void;
};

const CTA_DESTINATIONS = [
  {
    value: "vault",
    label: "Your Vault",
    valueHint: "Leave blank to open your Vault shop. Or paste a specific Vault link.",
    valuePlaceholder: "Leave blank for /@{username}/vault",
    labelPlaceholder: "Visit Vault",
  },
  {
    value: "events",
    label: "Upcoming events (this page)",
    valueHint: "Leave blank to scroll to Upcoming events on your Legacy Page.",
    valuePlaceholder: "#upcoming-events",
    labelPlaceholder: "View Events",
  },
  {
    value: "sponsors",
    label: "Sponsorship / brands",
    valueHint: "Leave blank for your sponsorship marketplace listing. Or paste a custom link.",
    valuePlaceholder: "Leave blank for brand inquiry page",
    labelPlaceholder: "Partner with us",
  },
  {
    value: "url",
    label: "External website",
    valueHint: "Full link fans open when they tap the button.",
    valuePlaceholder: "https://example.com/tickets",
    labelPlaceholder: "Buy tickets",
  },
  {
    value: "email",
    label: "Email",
    valueHint: "Opens the fan’s mail app to this address.",
    valuePlaceholder: "bookings@yourdomain.com",
    labelPlaceholder: "Email us",
  },
  {
    value: "path",
    label: "Page section or path",
    valueHint: "Use a section id (#contact) or an on-site path (/events/…). ",
    valuePlaceholder: "#sponsorship or /events/my-night",
    labelPlaceholder: "Learn more",
  },
] as const;

function destinationMeta(type: string) {
  return (
    CTA_DESTINATIONS.find((d) => d.value === type) ?? {
      value: type,
      label: type || "Custom",
      valueHint: "Where the button should send fans.",
      valuePlaceholder: "https://… or #section",
      labelPlaceholder: "Button text",
    }
  );
}

function CtaButtonFields({
  title,
  description,
  label,
  type,
  destination,
  onLabel,
  onType,
  onDestination,
}: {
  title: string;
  description: string;
  label: string;
  type: string;
  destination: string;
  onLabel: (v: string) => void;
  onType: (v: string) => void;
  onDestination: (v: string) => void;
}) {
  const meta = destinationMeta(type);
  const known = CTA_DESTINATIONS.some((d) => d.value === type);

  return (
    <div className="space-y-3 rounded-[var(--radius-md)] border border-border bg-card/40 p-4">
      <div>
        <h4 className="text-sm font-extrabold text-foreground">{title}</h4>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <Input
        label="Button text"
        value={label}
        onChange={(e) => onLabel(e.target.value)}
        placeholder={meta.labelPlaceholder}
        hint="Shown on the hero button on your public Legacy Page."
      />
      <Select
        label="Where it goes"
        value={known ? type : "__custom__"}
        onChange={(e) => {
          const next = e.target.value;
          if (next === "__custom__") return;
          onType(next);
          if (next === "events" && !destination.trim()) {
            onDestination("#upcoming-events");
          }
        }}
        hint="Pick a destination. Leave the link blank for Vault, events, or sponsorship defaults."
      >
        {CTA_DESTINATIONS.map((d) => (
          <option key={d.value} value={d.value}>
            {d.label}
          </option>
        ))}
        {!known && type ? (
          <option value="__custom__">Custom ({type})</option>
        ) : null}
      </Select>
      <Input
        label="Link or destination (optional for Vault / events / sponsorship)"
        value={destination}
        onChange={(e) => onDestination(e.target.value)}
        placeholder={meta.valuePlaceholder}
        hint={meta.valueHint}
      />
    </div>
  );
}

export function LegacyCtaSettingsEditor({ value, onChange }: Props) {
  function patch(partial: Partial<LegacyCtaDraft>) {
    onChange({ ...value, ...partial });
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-extrabold text-foreground">Hero buttons</h3>
        <p className="text-sm text-muted-foreground">
          Two buttons on your public Legacy Page (for example “Visit Vault” and “View Events”).
          Choose the label fans see and where each button goes.
        </p>
      </div>

      <CtaButtonFields
        title="Main button"
        description="Usually your strongest action — Vault, tickets, or bookings."
        label={value.primaryLabel}
        type={value.primaryType}
        destination={value.primaryValue}
        onLabel={(primaryLabel) => patch({ primaryLabel })}
        onType={(primaryType) => patch({ primaryType })}
        onDestination={(primaryValue) => patch({ primaryValue })}
      />

      <CtaButtonFields
        title="Second button"
        description="A supporting action — upcoming nights, contact, or another link."
        label={value.secondaryLabel}
        type={value.secondaryType}
        destination={value.secondaryValue}
        onLabel={(secondaryLabel) => patch({ secondaryLabel })}
        onType={(secondaryType) => patch({ secondaryType })}
        onDestination={(secondaryValue) => patch({ secondaryValue })}
      />

      <div className="space-y-3">
        <div>
          <h3 className="text-base font-extrabold text-foreground">Sponsorship</h3>
          <p className="text-sm text-muted-foreground">
            Tell brands whether you are open to partnerships on your Legacy Page.
          </p>
        </div>
        <label className="flex items-start gap-2 text-sm font-semibold text-foreground">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={value.sponsorshipAvailable}
            onChange={(e) => patch({ sponsorshipAvailable: e.target.checked })}
          />
          <span>
            Open to sponsorship
            <span className="mt-0.5 block font-normal text-muted-foreground">
              Shows an “open to brands” signal on your public page.
            </span>
          </span>
        </label>
        <Textarea
          label="Note for brands (optional)"
          rows={3}
          value={value.sponsorshipNote}
          onChange={(e) => patch({ sponsorshipNote: e.target.value })}
          placeholder="City nights, 800–1,200 typical turnout, brand-safe activations…"
          hint="Short pitch sponsors see with your sponsorship section."
          disabled={!value.sponsorshipAvailable}
        />
      </div>
    </div>
  );
}
