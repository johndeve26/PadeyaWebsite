"use client";

import { useState } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { Button } from "@/components/ui";
import { BlogBlockRenderer } from "@/components/blog/editor/BlogBlockRenderer";
import { BlogBlockToolbar } from "@/components/blog/editor/BlogBlockToolbar";
import {
  cloneBlockTree,
  createBlock,
  insertBlockAtRoot,
  removeBlockFromTree,
  updateBlockInTree,
  INSERTABLE_BLOCK_TYPES,
  type BlogBlock,
  type BlogContentDocument,
} from "@/lib/blog-document";

type Props = {
  document: BlogContentDocument;
  onChange: (doc: BlogContentDocument) => void;
  selectedBlockId: string | null;
  onSelectBlock: (id: string | null) => void;
  onDragActive?: (active: boolean) => void;
  onAiBlock?: (blockId: string) => void;
  devicePreview?: "desktop" | "tablet" | "mobile";
};

function SortableBlock({
  block,
  selected,
  onSelect,
  children,
}: {
  block: BlogBlock;
  selected: boolean;
  onSelect: () => void;
  children: React.ReactNode;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: block.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`rounded-[var(--radius-md)] border ${
        selected ? "border-primary ring-1 ring-primary/30" : "border-border"
      } bg-card text-card-foreground shadow-[var(--shadow-soft)] dark:bg-surface-elevated`}
      onClick={onSelect}
    >
      <div className="flex items-center gap-2 border-b border-border px-2 py-1">
        <button
          type="button"
          className="cursor-grab touch-none text-muted-foreground hover:text-foreground px-1 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
          aria-label={`Drag to reorder ${block.type.replace(/_/g, " ")} block`}
          {...attributes}
          {...listeners}
        >
          ⠿
        </button>
        <span className="text-xs text-muted-foreground capitalize flex-1">
          {block.type.replace(/_/g, " ")}
          {block.props.locked ? " 🔒" : ""}
        </span>
      </div>
      <div className="p-3">{children}</div>
    </div>
  );
}

export function BlogLayoutManager({
  document,
  onChange,
  selectedBlockId,
  onSelectBlock,
  onDragActive,
  onAiBlock,
  devicePreview = "desktop",
}: Props) {
  const [a11yMessage, setA11yMessage] = useState("");
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const widthClass =
    devicePreview === "mobile"
      ? "max-w-sm mx-auto"
      : devicePreview === "tablet"
        ? "max-w-2xl mx-auto"
        : "max-w-4xl mx-auto";

  const handleDragEnd = (event: DragEndEvent) => {
    onDragActive?.(false);
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const ids = document.blocks.map((b) => b.id);
    const oldIndex = ids.indexOf(String(active.id));
    const newIndex = ids.indexOf(String(over.id));
    if (oldIndex < 0 || newIndex < 0) return;
    const next = [...document.blocks];
    const [moved] = next.splice(oldIndex, 1);
    next.splice(newIndex, 0, moved);
    onChange({ ...document, blocks: next });
    setA11yMessage(
      `Moved ${String(active.id)} to position ${newIndex + 1} of ${next.length}`,
    );
  };

  const patchBlock = (id: string, patch: Partial<BlogBlock>) => {
    onChange({
      ...document,
      blocks: updateBlockInTree(document.blocks, id, (b) => ({ ...b, ...patch })),
    });
  };

  return (
    <div className={`${widthClass} px-4 py-6 transition-all`}>
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {a11yMessage}
      </div>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={() => onDragActive?.(true)}
        onDragEnd={handleDragEnd}
        onDragCancel={() => onDragActive?.(false)}
      >
        <SortableContext
          items={document.blocks.map((b) => b.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-4">
            {document.blocks.map((block) => (
              <SortableBlock
                key={block.id}
                block={block}
                selected={selectedBlockId === block.id}
                onSelect={() => onSelectBlock(block.id)}
              >
                <BlogBlockRenderer block={block} />
                <div className="mt-2 border-t border-border pt-2">
                  <BlogBlockToolbar
                    block={block}
                    compact
                    onDuplicate={() =>
                      onChange({
                        ...document,
                        blocks: insertBlockAtRoot(
                          document.blocks,
                          cloneBlockTree(block),
                        ),
                      })
                    }
                    onDelete={
                      !block.props.locked
                        ? () =>
                            onChange({
                              ...document,
                              blocks: removeBlockFromTree(document.blocks, block.id),
                            })
                        : undefined
                    }
                    onToggleLock={() =>
                      patchBlock(block.id, {
                        props: { ...block.props, locked: !block.props.locked },
                      })
                    }
                    onAi={onAiBlock ? () => onAiBlock(block.id) : undefined}
                  />
                </div>
              </SortableBlock>
            ))}
          </div>
        </SortableContext>
      </DndContext>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => {
            const b = createBlock("standard_section");
            onChange({
              ...document,
              blocks: insertBlockAtRoot(document.blocks, b),
            });
          }}
        >
          + Section
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => {
            const b = createBlock("two_column_row");
            onChange({
              ...document,
              blocks: insertBlockAtRoot(document.blocks, b),
            });
          }}
        >
          + Two columns
        </Button>
        {INSERTABLE_BLOCK_TYPES.filter((t) =>
          ["rich_text", "heading", "image", "quote"].includes(t),
        ).map((type) => (
          <Button
            key={type}
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              const b = createBlock(type);
              onChange({
                ...document,
                blocks: insertBlockAtRoot(document.blocks, b),
              });
            }}
          >
            + {type.replace(/_/g, " ")}
          </Button>
        ))}
      </div>
    </div>
  );
}
