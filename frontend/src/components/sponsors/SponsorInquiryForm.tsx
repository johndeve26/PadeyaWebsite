"use client";

import { Button, Input, Select, Textarea } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import type { SponsorshipSlot } from "@/lib/types/sponsorships";

export type SponsorInquiryFormValues = {
  company_name: string;
  contact_name: string;
  contact_email: string;
  website: string;
  message: string;
  proposed_budget: string;
};

export function SponsorInquiryForm({
  slot,
  values,
  onChange,
  onSubmit,
  busy,
  campaigns,
  campaignId,
  onCampaignChange,
}: {
  slot: SponsorshipSlot;
  values: SponsorInquiryFormValues;
  onChange: (next: SponsorInquiryFormValues) => void;
  onSubmit: () => void;
  busy: boolean;
  campaigns?: { id: string; name: string }[];
  campaignId?: string;
  onCampaignChange?: (campaignId: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="rounded-[var(--radius-md)] border border-border bg-muted/60 px-3 py-3 dark:bg-surface-elevated">
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Selected opportunity
        </p>
        <p className="mt-1 font-bold text-foreground">{slot.title}</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {slot.host_display_name || "Host"}
          {slot.host_username ? ` · @${slot.host_username.replace(/^@/, "")}` : ""}
          {slot.event_title ? ` · ${slot.event_title}` : ""}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {slot.slot_type_label} · {formatNgn(slot.price)}
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          Inquiries stay inside Pàdéyá. Host contact details are not exposed.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <Input
          label="Brand name"
          value={values.company_name}
          onChange={(e) =>
            onChange({ ...values, company_name: e.target.value })
          }
        />
        <Input
          label="Contact name"
          value={values.contact_name}
          onChange={(e) =>
            onChange({ ...values, contact_name: e.target.value })
          }
        />
        <Input
          label="Email"
          type="email"
          value={values.contact_email}
          onChange={(e) =>
            onChange({ ...values, contact_email: e.target.value })
          }
        />
        <Input
          label="Budget (optional)"
          hint="Helps hosts respond faster"
          value={values.proposed_budget}
          onChange={(e) =>
            onChange({ ...values, proposed_budget: e.target.value })
          }
        />
        <div className="md:col-span-2">
          {campaigns && campaigns.length > 0 && onCampaignChange ? (
            <label className="mb-3 block space-y-1 text-sm">
              <span className="font-semibold">Link to campaign (optional)</span>
              <Select
                value={campaignId ?? ""}
                onChange={(e) => onCampaignChange(e.target.value)}
                aria-label="Campaign"
              >
                <option value="">No campaign</option>
                {campaigns.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </label>
          ) : null}
          <Textarea
            label="Message"
            value={values.message}
            onChange={(e) => onChange({ ...values, message: e.target.value })}
            hint="Campaign goal, deliverables, and timeline"
          />
        </div>
        <div className="md:col-span-2">
          <Button disabled={busy} onClick={onSubmit}>
            {busy ? "Submitting…" : "Submit inquiry"}
          </Button>
        </div>
      </div>
    </div>
  );
}
