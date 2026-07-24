"use client";

import { Button, Input } from "@/components/ui";
import type { LegacySocialLink } from "@/lib/types/legacy";

type Draft = {
  platform: string;
  url: string;
  label: string;
};

type Props = {
  value: Draft[];
  onChange: (next: Draft[]) => void;
};

export function LegacySocialLinksEditor({ value, onChange }: Props) {
  function update(index: number, patch: Partial<Draft>) {
    onChange(value.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-extrabold text-foreground">Social links</h3>
          <p className="text-sm text-muted-foreground">Shown on your public Legacy Page.</p>
        </div>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={() =>
            onChange([...value, { platform: "instagram", url: "", label: "" }])
          }
        >
          Add link
        </Button>
      </div>
      {value.length === 0 ? (
        <p className="text-sm text-muted-foreground">No social links yet.</p>
      ) : null}
      {value.map((row, index) => (
        <div key={`${row.platform}-${index}`} className="grid gap-2 sm:grid-cols-[140px_1fr_auto]">
          <Input
            value={row.platform}
            placeholder="platform"
            onChange={(e) => update(index, { platform: e.target.value })}
          />
          <Input
            value={row.url}
            placeholder="https://"
            onChange={(e) => update(index, { url: e.target.value })}
          />
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => onChange(value.filter((_, i) => i !== index))}
          >
            Remove
          </Button>
        </div>
      ))}
    </div>
  );
}

export function socialLinksToDraft(links: LegacySocialLink[] | undefined): Draft[] {
  return (links ?? []).map((l) => ({
    platform: l.platform,
    url: l.url,
    label: l.label ?? "",
  }));
}
