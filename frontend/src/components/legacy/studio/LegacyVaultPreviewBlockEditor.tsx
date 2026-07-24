"use client";

import { useState } from "react";

import { Button, Input, Textarea } from "@/components/ui";
import {
  VAULT_PREVIEW_LAYOUTS,
  type LegacyContentBlock,
  type LegacyVaultPreviewCard,
} from "@/lib/types/legacy";

type Props = {
  block: LegacyContentBlock;
  vaultItems: LegacyVaultPreviewCard[];
  busy?: boolean;
  onSave: (patch: Record<string, unknown>) => void;
};

function selectedIdsFromConfig(config: Record<string, unknown> | null): string[] {
  const raw = config?.vault_item_ids;
  if (!Array.isArray(raw)) return [];
  return raw.map((id) => String(id)).filter(Boolean);
}

export function LegacyVaultPreviewBlockEditor({
  block,
  vaultItems,
  busy,
  onSave,
}: Props) {
  const [title, setTitle] = useState(block.title_override ?? "");
  const [description, setDescription] = useState(block.description_override ?? "");
  const [sourceType, setSourceType] = useState(block.source_type || "automatic");
  const [layoutStyle, setLayoutStyle] = useState(
    VAULT_PREVIEW_LAYOUTS.some((l) => l.value === block.layout_style)
      ? block.layout_style
      : "locked_cards",
  );
  const [itemLimit, setItemLimit] = useState(
    block.item_limit != null ? String(block.item_limit) : "3",
  );
  const [selectedIds, setSelectedIds] = useState<string[]>(() =>
    selectedIdsFromConfig(block.config),
  );

  function toggleItem(id: string) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  function moveSelected(id: string, direction: -1 | 1) {
    setSelectedIds((prev) => {
      const index = prev.indexOf(id);
      const target = index + direction;
      if (index < 0 || target < 0 || target >= prev.length) return prev;
      const next = [...prev];
      const [row] = next.splice(index, 1);
      next.splice(target, 0, row);
      return next;
    });
  }

  function save() {
    const limitRaw = itemLimit.trim();
    const limit = limitRaw ? Number(limitRaw) : null;
    const nextConfig = {
      ...(block.config ?? {}),
      vault_item_ids: sourceType === "manual" ? selectedIds : selectedIdsFromConfig(block.config),
    };
    onSave({
      title_override: title.trim() || null,
      description_override: description.trim() || null,
      source_type: sourceType,
      layout_style: layoutStyle,
      item_limit: Number.isFinite(limit) ? limit : null,
      config: nextConfig,
    });
  }

  return (
    <div className="space-y-4 border-t border-border pt-4">
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
        Vault Preview settings
      </p>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1.5 text-sm font-semibold text-foreground sm:col-span-2">
          Block title
          <Input
            value={title}
            disabled={busy}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Vault"
          />
        </label>
        <label className="space-y-1.5 text-sm font-semibold text-foreground sm:col-span-2">
          Block description
          <Textarea
            rows={2}
            value={description}
            disabled={busy}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Exclusive drops fans unlock…"
          />
        </label>
        <label className="space-y-1.5 text-sm font-semibold text-foreground">
          Source
          <select
            className="w-full rounded-[var(--radius-md)] border border-input-border bg-input-background px-3 py-2 text-sm text-input-foreground"
            value={sourceType}
            disabled={busy}
            onChange={(e) => setSourceType(e.target.value)}
          >
            <option value="automatic">Automatic — featured + newest</option>
            <option value="manual">Manual — choose drops</option>
          </select>
        </label>
        <label className="space-y-1.5 text-sm font-semibold text-foreground">
          Layout style
          <select
            className="w-full rounded-[var(--radius-md)] border border-input-border bg-input-background px-3 py-2 text-sm text-input-foreground"
            value={layoutStyle}
            disabled={busy}
            onChange={(e) => setLayoutStyle(e.target.value)}
          >
            {VAULT_PREVIEW_LAYOUTS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1.5 text-sm font-semibold text-foreground">
          Item limit
          <Input
            type="number"
            min={1}
            max={12}
            value={itemLimit}
            disabled={busy}
            onChange={(e) => setItemLimit(e.target.value)}
          />
        </label>
      </div>

      {sourceType === "manual" ? (
        <div className="space-y-2">
          <p className="text-sm font-semibold text-foreground">
            Drops in Vault Preview
          </p>
          <p className="text-xs leading-relaxed text-muted-foreground">
            Select published teasers only. Locked bodies never appear on Legacy. A featured
            Vault item (sidebar) still pins first when set.
          </p>
          {vaultItems.length === 0 ? (
            <p className="text-sm text-muted-foreground">No published Vault drops yet.</p>
          ) : (
            <ul className="space-y-2">
              {vaultItems.map((item) => {
                const checked = selectedIds.includes(item.id);
                const order = selectedIds.indexOf(item.id);
                return (
                  <li
                    key={item.id}
                    className="flex flex-wrap items-center gap-2 rounded-[var(--radius-md)] border border-border px-3 py-2"
                  >
                    <label className="flex min-w-0 flex-1 items-center gap-2 text-sm font-semibold text-foreground">
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={busy}
                        onChange={() => toggleItem(item.id)}
                      />
                      <span className="truncate">{item.title}</span>
                    </label>
                    {checked ? (
                      <div className="flex items-center gap-1">
                        <span className="text-xs font-bold text-muted-foreground">
                          #{order + 1}
                        </span>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={busy || order <= 0}
                          onClick={() => moveSelected(item.id, -1)}
                        >
                          Up
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={busy || order >= selectedIds.length - 1}
                          onClick={() => moveSelected(item.id, 1)}
                        >
                          Down
                        </Button>
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      ) : (
        <p className="text-sm leading-relaxed text-muted-foreground">
          Automatic mode shows your featured Vault item first, then the newest published
          drops (up to the item limit).
        </p>
      )}

      <Button size="sm" disabled={busy} onClick={save}>
        Save Vault Preview
      </Button>
    </div>
  );
}
