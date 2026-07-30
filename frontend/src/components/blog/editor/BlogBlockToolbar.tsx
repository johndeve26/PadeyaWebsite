"use client";

import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";
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
      className={cn(
        "flex flex-wrap items-center gap-1",
        compact ? "text-xs" : "",
        compact &&
          "w-full justify-end border-t border-border/60 pt-2 sm:w-auto sm:border-0 sm:pt-0",
      )}
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
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onDuplicate}
          aria-label="Duplicate block"
          className="px-2 sm:px-3"
        >
          <span className="sm:hidden" aria-hidden>
            ⧉
          </span>
          <span className="hidden sm:inline">Duplicate</span>
        </Button>
      ) : null}
      {onToggleLock ? (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onToggleLock}
          aria-pressed={locked}
          aria-label={locked ? "Unlock block" : "Lock block"}
          className="px-2 sm:px-3"
        >
          {locked ? "🔒" : <span className="hidden sm:inline">Unlock</span>}
          {!locked ? (
            <span className="sm:hidden" aria-hidden>
              🔓
            </span>
          ) : null}
        </Button>
      ) : null}
      {onAi ? (
        <Button type="button" variant="ghost" size="sm" onClick={onAi} aria-label="AI assist">
          AI
        </Button>
      ) : null}
      {onSettings ? (
        <Button type="button" variant="ghost" size="sm" onClick={onSettings} aria-label="Block settings">
          <span className="sm:hidden" aria-hidden>
            ⚙
          </span>
          <span className="hidden sm:inline">Settings</span>
        </Button>
      ) : null}
      {onDelete && !locked ? (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onDelete}
          aria-label="Delete block"
          className="px-2 sm:px-3"
        >
          <span className="sm:hidden" aria-hidden>
            ✕
          </span>
          <span className="hidden sm:inline">Delete</span>
        </Button>
      ) : null}
    </div>
  );
}
