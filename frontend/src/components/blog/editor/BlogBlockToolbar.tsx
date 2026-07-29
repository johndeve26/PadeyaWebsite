"use client";

import { Button } from "@/components/ui";
import type { BlogBlock } from "@/lib/blog-document";
import { isBlockLocked } from "@/lib/blog-document";

type Props = {
  block: BlogBlock;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  onDuplicate?: () => void;
  onDelete?: () => void;
  onToggleLock?: () => void;
  onAi?: () => void;
  onSettings?: () => void;
  compact?: boolean;
};

export function BlogBlockToolbar({
  block,
  onMoveUp,
  onMoveDown,
  onDuplicate,
  onDelete,
  onToggleLock,
  onAi,
  onSettings,
  compact,
}: Props) {
  const locked = isBlockLocked(block);
  return (
    <div
      className={`flex flex-wrap items-center gap-1 ${compact ? "text-xs" : ""}`}
      role="toolbar"
      aria-label="Block actions"
    >
      {onMoveUp ? (
        <Button type="button" variant="ghost" size="sm" onClick={onMoveUp} aria-label="Move up">
          ↑
        </Button>
      ) : null}
      {onMoveDown ? (
        <Button type="button" variant="ghost" size="sm" onClick={onMoveDown} aria-label="Move down">
          ↓
        </Button>
      ) : null}
      {onDuplicate ? (
        <Button type="button" variant="ghost" size="sm" onClick={onDuplicate}>
          Duplicate
        </Button>
      ) : null}
      {onToggleLock ? (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onToggleLock}
          aria-pressed={locked}
        >
          {locked ? "🔒" : "Unlock"}
        </Button>
      ) : null}
      {onAi ? (
        <Button type="button" variant="ghost" size="sm" onClick={onAi}>
          AI
        </Button>
      ) : null}
      {onSettings ? (
        <Button type="button" variant="ghost" size="sm" onClick={onSettings}>
          Settings
        </Button>
      ) : null}
      {onDelete && !locked ? (
        <Button type="button" variant="ghost" size="sm" onClick={onDelete}>
          Delete
        </Button>
      ) : null}
    </div>
  );
}
