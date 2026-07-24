"use client";

import { useState } from "react";

import { LegacyBlockCard } from "@/components/legacy/studio/LegacyBlockCard";
import { Alert } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  reorderLegacyContentBlocks,
  toggleLegacyContentBlock,
  updateLegacyContentBlock,
} from "@/lib/legacy-api";
import type { LegacyContentBlock, LegacyVaultPreviewCard } from "@/lib/types/legacy";

type Props = {
  initialBlocks: LegacyContentBlock[];
  vaultItems?: LegacyVaultPreviewCard[];
  onChange?: (blocks: LegacyContentBlock[]) => void;
};

export function LegacyContentBlockManager({
  initialBlocks,
  vaultItems = [],
  onChange,
}: Props) {
  const [blocks, setBlocks] = useState(initialBlocks);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function commit(next: LegacyContentBlock[]) {
    setBlocks(next);
    onChange?.(next);
  }

  async function onToggle(block: LegacyContentBlock) {
    setBusyId(block.id);
    setError(null);
    try {
      const updated = await toggleLegacyContentBlock(block.id);
      commit(blocks.map((b) => (b.id === block.id ? updated : b)));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Toggle failed");
    } finally {
      setBusyId(null);
    }
  }

  async function onSave(block: LegacyContentBlock, patch: Record<string, unknown>) {
    setBusyId(block.id);
    setError(null);
    try {
      const updated = await updateLegacyContentBlock(block.id, patch);
      commit(blocks.map((b) => (b.id === block.id ? updated : b)));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    } finally {
      setBusyId(null);
    }
  }

  async function move(blockId: string, direction: -1 | 1) {
    const index = blocks.findIndex((b) => b.id === blockId);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= blocks.length) return;
    const ordered = [...blocks];
    const [row] = ordered.splice(index, 1);
    ordered.splice(target, 0, row);
    setBusyId(blockId);
    setError(null);
    try {
      const next = await reorderLegacyContentBlocks(ordered.map((b) => b.id));
      commit(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Reorder failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-4">
      {error ? (
        <Alert tone="danger" title="Content blocks">
          {error}
        </Alert>
      ) : null}
      <p className="text-sm leading-relaxed text-muted-foreground">
        Control what appears on your public Legacy Page. Reorder blocks, override titles,
        and toggle visibility. Hiding Verified Reviews never deletes attendee feedback.
      </p>
      {blocks.map((block) => (
        <LegacyBlockCard
          key={block.id}
          block={block}
          vaultItems={vaultItems}
          busy={busyId === block.id}
          onToggle={() => void onToggle(block)}
          onMoveUp={() => void move(block.id, -1)}
          onMoveDown={() => void move(block.id, 1)}
          onSave={(patch) => void onSave(block, patch)}
        />
      ))}
    </div>
  );
}
