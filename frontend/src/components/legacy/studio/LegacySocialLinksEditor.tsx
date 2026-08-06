"use client";

import { Button, Input, Select } from "@/components/ui";
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

const PLATFORMS = [
  { value: "instagram", label: "Instagram" },
  { value: "tiktok", label: "TikTok" },
  { value: "x", label: "X / Twitter" },
  { value: "youtube", label: "YouTube" },
  { value: "facebook", label: "Facebook" },
  { value: "spotify", label: "Spotify" },
  { value: "soundcloud", label: "SoundCloud" },
  { value: "website", label: "Website" },
  { value: "other", label: "Other" },
] as const;

export function LegacySocialLinksEditor({ value, onChange }: Props) {
  function update(index: number, patch: Partial<Draft>) {
    onChange(value.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-extrabold text-foreground">Social links</h3>
          <p className="text-sm text-muted-foreground">
            Profile links shown on your public Legacy Page so fans can follow you.
          </p>
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
      {value.map((row, index) => {
        const known = PLATFORMS.some((p) => p.value === row.platform);
        return (
          <div
            key={`${row.platform}-${index}`}
            className="grid gap-2 rounded-[var(--radius-md)] border border-border p-3 sm:grid-cols-[160px_1fr_auto]"
          >
            <Select
              label="Platform"
              value={known ? row.platform : "other"}
              onChange={(e) => {
                const next = e.target.value;
                update(index, {
                  platform: next === "other" && !known ? row.platform || "other" : next,
                });
              }}
            >
              {PLATFORMS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </Select>
            <Input
              label="Profile URL"
              value={row.url}
              placeholder="https://instagram.com/yourhandle"
              onChange={(e) => update(index, { url: e.target.value })}
              hint="Full https link to your profile or page."
            />
            <div className="flex items-end">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => onChange(value.filter((_, i) => i !== index))}
              >
                Remove
              </Button>
            </div>
            {!known && row.platform ? (
              <Input
                className="sm:col-span-2"
                label="Custom platform name"
                value={row.platform}
                placeholder="e.g. bandcamp"
                onChange={(e) => update(index, { platform: e.target.value })}
              />
            ) : null}
          </div>
        );
      })}
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

export function socialLinksToDraft(links: LegacySocialLink[] | undefined): Draft[] {
  return (links ?? []).map((l) => ({
    platform: l.platform,
    url: l.url,
    label: l.label ?? "",
  }));
}
