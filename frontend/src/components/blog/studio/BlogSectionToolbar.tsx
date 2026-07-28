"use client";

import { Button } from "@/components/ui";

import type { MarkdownSection } from "./markdown-utils";

export function BlogSectionToolbar({
  sections,
  lockedHeadings,
  busy,
  onRegenerate,
  onRewrite,
  onExpand,
  onShorten,
  onMove,
  onDelete,
  onDuplicate,
  onAddBelow,
  onToggleLock,
}: {
  sections: MarkdownSection[];
  lockedHeadings: string[];
  busy?: boolean;
  onRegenerate: (index: number) => void;
  onRewrite: (index: number) => void;
  onExpand: (index: number) => void;
  onShorten: (index: number) => void;
  onMove: (index: number, direction: -1 | 1) => void;
  onDelete: (index: number) => void;
  onDuplicate: (index: number) => void;
  onAddBelow: (index: number) => void;
  onToggleLock: (heading: string) => void;
}) {
  if (sections.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        Add ## headings in the markdown body to enable section controls.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {sections.map((sec) => {
        const locked = lockedHeadings.includes(sec.heading);
        return (
          <li
            key={`${sec.index}-${sec.heading}`}
            className="rounded-[var(--radius-sm)] border border-border bg-surface-muted/30 px-2 py-2"
          >
            <p className="mb-1.5 truncate text-xs font-semibold text-foreground">
              {sec.heading}
              {locked ? (
                <span className="ml-2 text-[10px] font-bold uppercase text-muted-foreground">
                  Locked
                </span>
              ) : null}
            </p>
            <div className="flex flex-wrap gap-1">
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || locked}
                onClick={() => onRegenerate(sec.index)}
              >
                Regenerate
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || locked}
                onClick={() => onRewrite(sec.index)}
              >
                Rewrite
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || locked}
                onClick={() => onExpand(sec.index)}
              >
                Expand
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || locked}
                onClick={() => onShorten(sec.index)}
              >
                Shorten
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || sec.index === 0}
                onClick={() => onMove(sec.index, -1)}
              >
                Up
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || sec.index === sections.length - 1}
                onClick={() => onMove(sec.index, 1)}
              >
                Down
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy}
                onClick={() => onDuplicate(sec.index)}
              >
                Duplicate
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy}
                onClick={() => onAddBelow(sec.index)}
              >
                Add below
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={busy}
                onClick={() => onToggleLock(sec.heading)}
              >
                {locked ? "Unlock" : "Lock"}
              </Button>
              <Button
                size="sm"
                variant="danger"
                disabled={busy}
                onClick={() => onDelete(sec.index)}
              >
                Delete
              </Button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
