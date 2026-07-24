"use client";

import { useState } from "react";

import { HostSponsorshipPitchAIAssist } from "@/components/host/sponsorships/HostSponsorshipPitchAIAssist";
import { Button, Card, Input, Select, Textarea } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import { SPONSORSHIP_HOSTS_PATH } from "@/lib/sponsor-marketplace-paths";
import {
  SPONSORSHIP_SLOT_TYPES,
  type SponsorshipSlotFormValues,
} from "@/lib/sponsorship-slot-form";

type Props = {
  mode: "create" | "edit";
  initial: SponsorshipSlotFormValues;
  busy?: boolean;
  submitLabel: string;
  onSubmit: (values: SponsorshipSlotFormValues) => void | Promise<void>;
};

export function HostSponsorshipSlotForm({
  mode,
  initial,
  busy = false,
  submitLabel,
  onSubmit,
}: Props) {
  const [slotType, setSlotType] = useState(initial.slot_type);
  const [title, setTitle] = useState(initial.title);
  const [description, setDescription] = useState(initial.description);
  const [price, setPrice] = useState(initial.price);
  const [publish, setPublish] = useState(Boolean(initial.publish));
  const [aiNotes, setAiNotes] = useState("");

  const selectedLabel =
    SPONSORSHIP_SLOT_TYPES.find((t) => t.value === slotType)?.label ?? slotType;
  const canSubmit =
    Boolean(title.trim()) &&
    Boolean(description.trim()) &&
    Boolean(price.trim()) &&
    !busy;

  return (
    <div className="grid w-full gap-6 lg:grid-cols-12 lg:items-start">
      <Card className="space-y-5 lg:col-span-7">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Package details
          </p>
          <h2 className="mt-1 text-xl font-extrabold text-foreground">
            {mode === "create" ? "New slot listing" : "Edit slot listing"}
          </h2>
        </div>

        <Select
          label="Slot type"
          value={slotType}
          onChange={(e) => setSlotType(e.target.value)}
        >
          {SPONSORSHIP_SLOT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </Select>

        <HostSponsorshipPitchAIAssist
          compact
          slotType={slotType}
          slotTypeLabel={selectedLabel}
          hostNotes={aiNotes}
          onApply={(patch) => {
            if (patch.slotTitle) setTitle(patch.slotTitle);
            const desc = patch.slotDescription || patch.pitch;
            if (desc) setDescription(desc);
          }}
        />
        <Textarea
          label="Notes for AI (optional)"
          value={aiNotes}
          onChange={(e) => setAiNotes(e.target.value)}
          hint="Package angle for draft copy — save the slot manually when ready."
          className="min-h-[72px]"
        />

        <Input
          label="Title"
          placeholder="e.g. Title partner — Detty Friday"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />

        <Textarea
          label="Description"
          hint="Spell out deliverables, timing, and what the brand receives."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        <Input
          label="Price (NGN)"
          placeholder="250000"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />

        {mode === "create" ? (
          <label className="flex cursor-pointer items-start gap-3 rounded-[var(--radius-md)] border border-border bg-muted px-4 py-3 text-sm">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-[var(--brand-green)]"
              checked={publish}
              onChange={(e) => setPublish(e.target.checked)}
            />
            <span>
              <span className="font-bold text-foreground">
                Publish immediately
              </span>
              <span className="mt-0.5 block text-muted-foreground">
                Verified hosts only. Drafts stay private until you publish.
              </span>
            </span>
          </label>
        ) : null}

        <Button
          disabled={!canSubmit}
          onClick={() =>
            void onSubmit({
              slot_type: slotType,
              title: title.trim(),
              description: description.trim(),
              price: price.trim(),
              publish: mode === "create" ? publish : undefined,
            })
          }
        >
          {busy
            ? "Saving…"
            : mode === "create"
              ? publish
                ? "Create & publish"
                : "Save as draft"
              : submitLabel}
        </Button>
      </Card>

      <div className="space-y-4 lg:col-span-5">
        <Card variant="dark" className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-accent">
            Brand preview
          </p>
          <h3 className="text-lg font-extrabold text-paper">
            {title.trim() || "Your package title"}
          </h3>
          <p className="text-sm text-subtle-foreground">{selectedLabel}</p>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-subtle-foreground">
            {description.trim() ||
              "Describe the placement so brands know exactly what they’re inquiring about."}
          </p>
          <p className="inline-flex rounded-[var(--radius-md)] bg-accent px-3 py-1.5 text-sm font-extrabold text-primary-foreground">
            {price.trim() ? formatNgn(price) : "—"}
          </p>
        </Card>

        <Card className="space-y-2">
          <h3 className="font-bold text-foreground">Tips for better inquiries</h3>
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-muted-foreground">
            <li>Name the event or surface (Legacy, Vault, ticket email).</li>
            <li>Include audience fit and expected exposure.</li>
            <li>Set a realistic NGN price brands can respond to.</li>
            <li>Keep accepting sponsors on so you appear in {SPONSORSHIP_HOSTS_PATH}.</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
