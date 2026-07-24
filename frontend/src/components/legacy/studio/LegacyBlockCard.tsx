"use client";

import { Button, Card, Input, Textarea } from "@/components/ui";
import { LegacyVaultPreviewBlockEditor } from "@/components/legacy/studio/LegacyVaultPreviewBlockEditor";
import { LegacyVisibilityToggle } from "@/components/legacy/studio/LegacyVisibilityToggle";
import {
  BLOCK_TYPE_HINTS,
  BLOCK_TYPE_LABELS,
  type LegacyContentBlock,
  type LegacyVaultPreviewCard,
} from "@/lib/types/legacy";

type Props = {
  block: LegacyContentBlock;
  vaultItems?: LegacyVaultPreviewCard[];
  busy?: boolean;
  onToggle: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onSave: (patch: Record<string, unknown>) => void;
};

export function LegacyBlockCard({
  block,
  vaultItems = [],
  busy,
  onToggle,
  onMoveUp,
  onMoveDown,
  onSave,
}: Props) {
  const label = BLOCK_TYPE_LABELS[block.block_type] ?? block.block_type;
  const hint = BLOCK_TYPE_HINTS[block.block_type] ?? "";
  const isVault = block.block_type === "vault_preview";

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-extrabold tracking-tight text-foreground">
              {label}
            </h3>
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-bold uppercase tracking-wide text-muted-foreground">
              {block.layout_style}
            </span>
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-bold uppercase tracking-wide text-muted-foreground">
              {block.source_type}
            </span>
          </div>
          {hint ? <p className="text-sm leading-relaxed text-muted-foreground">{hint}</p> : null}
        </div>
        <LegacyVisibilityToggle
          checked={block.is_visible}
          disabled={busy}
          onChange={() => onToggle()}
        />
      </div>

      {isVault ? (
        <LegacyVaultPreviewBlockEditor
          key={`${block.id}-${block.updated_at ?? ""}-${block.source_type}`}
          block={block}
          vaultItems={vaultItems}
          busy={busy}
          onSave={onSave}
        />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1.5 text-sm font-semibold text-foreground">
              Title override
              <Input
                defaultValue={block.title_override ?? ""}
                disabled={busy}
                onBlur={(e) => {
                  const value = e.target.value.trim() || null;
                  if (value !== (block.title_override ?? null)) {
                    onSave({ title_override: value });
                  }
                }}
              />
            </label>
            <label className="space-y-1.5 text-sm font-semibold text-foreground">
              Layout style
              <Input
                defaultValue={block.layout_style}
                disabled={busy}
                onBlur={(e) => {
                  const value = e.target.value.trim() || "default";
                  if (value !== block.layout_style) onSave({ layout_style: value });
                }}
              />
            </label>
            <label className="space-y-1.5 text-sm font-semibold text-foreground">
              Source
              <select
                className="w-full rounded-[var(--radius-md)] border border-input-border bg-input-background px-3 py-2 text-sm text-input-foreground"
                defaultValue={block.source_type}
                disabled={busy}
                onChange={(e) => onSave({ source_type: e.target.value })}
              >
                <option value="automatic">Automatic</option>
                <option value="manual">Manual</option>
              </select>
            </label>
            <label className="space-y-1.5 text-sm font-semibold text-foreground">
              Item limit
              <Input
                type="number"
                min={1}
                max={50}
                defaultValue={block.item_limit ?? ""}
                disabled={busy}
                placeholder="No limit"
                onBlur={(e) => {
                  const raw = e.target.value.trim();
                  const next = raw ? Number(raw) : null;
                  if (next !== block.item_limit) onSave({ item_limit: next });
                }}
              />
            </label>
          </div>

          <label className="block space-y-1.5 text-sm font-semibold text-foreground">
            Description override
            <Textarea
              rows={2}
              defaultValue={block.description_override ?? ""}
              disabled={busy}
              onBlur={(e) => {
                const value = e.target.value.trim() || null;
                if (value !== (block.description_override ?? null)) {
                  onSave({ description_override: value });
                }
              }}
            />
          </label>
        </>
      )}

      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="secondary" disabled={busy} onClick={onMoveUp}>
          Move up
        </Button>
        <Button size="sm" variant="secondary" disabled={busy} onClick={onMoveDown}>
          Move down
        </Button>
      </div>
    </Card>
  );
}
