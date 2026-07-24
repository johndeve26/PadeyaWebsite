"use client";

import { Button, Input } from "@/components/ui";
import { ImageUrlOrUploadField } from "@/components/media/ImageUrlOrUploadField";
import type { VaultMediaDraft } from "@/lib/types/vault";

type Props = {
  value: VaultMediaDraft[];
  onChange: (next: VaultMediaDraft[]) => void;
};

export function VaultMediaEditor({ value, onChange }: Props) {
  function update(index: number, patch: Partial<VaultMediaDraft>) {
    onChange(value.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function move(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= value.length) return;
    const next = [...value];
    const [row] = next.splice(index, 1);
    next.splice(target, 0, row);
    onChange(next.map((r, i) => ({ ...r, sort_order: i })));
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-extrabold text-foreground">Media assets</h3>
          <p className="text-sm text-muted-foreground">
            Preview media stays visible when locked. Full assets stay protected.
          </p>
        </div>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={() =>
            onChange([
              ...value,
              {
                url: "",
                media_type: "image",
                label: "",
                is_preview: false,
                sort_order: value.length,
              },
            ])
          }
        >
          Add media
        </Button>
      </div>

      {value.length === 0 ? (
        <p className="text-sm text-muted-foreground">No media attached yet.</p>
      ) : null}

      {value.map((row, index) => (
        <div
          key={`media-${index}`}
          className="space-y-3 rounded-[var(--radius-lg)] border border-border p-4"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <ImageUrlOrUploadField
              label="Image"
              hint="Upload or paste a URL for this asset."
              value={row.url}
              onChange={(url) => update(index, { url })}
              mediaType={row.media_type === "image" ? "other" : "gallery"}
              previewClassName="h-14 w-20"
            />
            <Input
              label="Media type"
              value={row.media_type}
              onChange={(e) => update(index, { media_type: e.target.value })}
              placeholder="image, video, audio, file"
            />
            <Input
              label="Label"
              value={row.label}
              onChange={(e) => update(index, { label: e.target.value })}
              placeholder="Optional"
            />
            <label className="flex items-center gap-2 self-end pb-2 text-sm font-semibold text-foreground">
              <input
                type="checkbox"
                checked={row.is_preview}
                onChange={(e) => update(index, { is_preview: e.target.checked })}
              />
              Public preview asset
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" variant="ghost" onClick={() => move(index, -1)}>
              Move up
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => move(index, 1)}>
              Move down
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => onChange(value.filter((_, i) => i !== index))}
            >
              Remove
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
