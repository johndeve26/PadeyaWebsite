"use client";

import { useCallback, useState } from "react";

import { Button, Textarea } from "@/components/ui";
import { BlogBlockToolbar } from "@/components/blog/editor/BlogBlockToolbar";
import {
  createBlock,
  flattenBlocksForStandard,
  insertBlockAtRoot,
  removeBlockFromTree,
  updateBlockInTree,
  cloneBlockTree,
  SLASH_COMMANDS,
  type BlogBlock,
  type BlogContentDocument,
} from "@/lib/blog-document";

type Props = {
  document: BlogContentDocument;
  onChange: (doc: BlogContentDocument) => void;
  selectedBlockId: string | null;
  onSelectBlock: (id: string | null) => void;
  onAiBlock?: (blockId: string) => void;
  distractionFree?: boolean;
};

export function StandardBlogEditor({
  document,
  onChange,
  selectedBlockId,
  onSelectBlock,
  onAiBlock,
}: Props) {
  const [slashOpen, setSlashOpen] = useState<string | null>(null);

  const blocks = flattenBlocksForStandard(document.blocks);

  const patchBlock = useCallback(
    (id: string, updater: (b: BlogBlock) => BlogBlock) => {
      onChange({
        ...document,
        blocks: updateBlockInTree(document.blocks, id, updater),
      });
    },
    [document, onChange],
  );

  const handleSlash = (blockId: string, command: string) => {
    const cmd = SLASH_COMMANDS.find((c) => c.command === command);
    if (!cmd) return;
    const newBlock = createBlock(cmd.type);
    const idx = document.blocks.findIndex((b) => b.id === blockId);
    onChange({
      ...document,
      blocks: insertBlockAtRoot(document.blocks, newBlock, idx >= 0 ? idx + 1 : undefined),
    });
    setSlashOpen(null);
    onSelectBlock(newBlock.id);
  };

  const moveBlock = (id: string, dir: -1 | 1) => {
    const flat = flattenBlocksForStandard(document.blocks);
    const idx = flat.findIndex((b) => b.id === id);
    if (idx < 0) return;
    const target = idx + dir;
    if (target < 0 || target >= flat.length) return;
    // Reorder at root level for simplicity in standard mode
    const rootIds = document.blocks.map((b) => b.id);
    const ri = rootIds.indexOf(id);
    if (ri < 0) return;
    const next = [...document.blocks];
    const swap = ri + dir;
    if (swap < 0 || swap >= next.length) return;
    [next[ri], next[swap]] = [next[swap], next[ri]];
    onChange({ ...document, blocks: next });
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
      {blocks.map((block) => {
        const selected = selectedBlockId === block.id;
        const isRich =
          block.type === "rich_text" ||
          block.type === "legacy_rich_text" ||
          block.type === "heading";

        return (
          <div
            key={block.id}
            className={`group rounded-[var(--radius-md)] border transition-colors ${
              selected ? "border-primary bg-surface/80" : "border-transparent hover:border-border"
            } ${block.props._layoutBound ? "border-dashed border-border/60" : ""}`}
            onClick={() => onSelectBlock(block.id)}
          >
            <div className="flex items-start gap-2 p-2">
              <span
                className="cursor-grab text-muted opacity-0 group-hover:opacity-100 select-none"
                aria-hidden
              >
                ⠿
              </span>
              <div className="min-w-0 flex-1 space-y-2">
                {block.type === "heading" ? (
                  <input
                    className="w-full bg-transparent font-display text-xl font-semibold outline-none"
                    value={String(block.content.text || "")}
                    onChange={(e) =>
                      patchBlock(block.id, (b) => ({
                        ...b,
                        content: { ...b.content, text: e.target.value },
                      }))
                    }
                    placeholder="Heading"
                  />
                ) : null}

                {isRich && block.type !== "heading" ? (
                  <Textarea
                    rows={6}
                    className="font-mono text-sm"
                    value={String(block.content.markdown || "")}
                    onChange={(e) => {
                      const val = e.target.value;
                      patchBlock(block.id, (b) => ({
                        ...b,
                        content: { ...b.content, markdown: val },
                      }));
                      if (val.endsWith("/") && val.length > 1) {
                        setSlashOpen(block.id);
                      } else if (slashOpen === block.id) {
                        setSlashOpen(null);
                      }
                    }}
                    placeholder="Write in markdown. Type / for commands…"
                  />
                ) : null}

                {slashOpen === block.id ? (
                  <div
                    className="rounded-[var(--radius-md)] border border-border bg-surface shadow-[var(--shadow-soft)] p-2"
                    role="listbox"
                  >
                    {SLASH_COMMANDS.map((cmd) => (
                      <button
                        key={cmd.command}
                        type="button"
                        className="block w-full text-left px-2 py-1.5 text-sm rounded hover:bg-muted/40"
                        onClick={() => handleSlash(block.id, cmd.command)}
                      >
                        /{cmd.command} — {cmd.label}
                      </button>
                    ))}
                  </div>
                ) : null}

                {block.props._layoutBound ? (
                  <p className="text-xs text-muted">Layout section (switch to Layout Manager to rearrange columns)</p>
                ) : null}
              </div>
              <BlogBlockToolbar
                block={block}
                compact
                onMoveUp={() => moveBlock(block.id, -1)}
                onMoveDown={() => moveBlock(block.id, 1)}
                onDuplicate={() =>
                  onChange({
                    ...document,
                    blocks: insertBlockAtRoot(document.blocks, cloneBlockTree(block)),
                  })
                }
                onDelete={() =>
                  onChange({
                    ...document,
                    blocks: removeBlockFromTree(document.blocks, block.id),
                  })
                }
                onToggleLock={() =>
                  patchBlock(block.id, (b) => ({
                    ...b,
                    props: { ...b.props, locked: !b.props.locked },
                  }))
                }
                onAi={onAiBlock ? () => onAiBlock(block.id) : undefined}
              />
            </div>
          </div>
        );
      })}

      <Button
        type="button"
        variant="secondary"
        className="w-full"
        onClick={() => {
          const b = createBlock("rich_text");
          onChange({
            ...document,
            blocks: insertBlockAtRoot(document.blocks, b),
          });
          onSelectBlock(b.id);
        }}
      >
        + Add paragraph
      </Button>
    </div>
  );
}
