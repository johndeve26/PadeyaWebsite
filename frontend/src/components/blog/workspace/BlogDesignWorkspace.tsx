"use client";
// BlogDesignWorkspace — Design tab: library panel + layout canvas + block inspector

import { useState } from "react";
import { useBlogStudio } from "@/components/blog/studio/BlogStudioProvider";
import {
  BlogLayoutManager,
  BlogBlockSettings,
  BlogTemplateLibrary,
  BlogReusableSectionsPanel,
} from "@/components/blog/editor";
import { findBlockById, updateBlockInTree } from "@/lib/blog-document";
import { useDocumentHistory } from "@/components/blog/editor/useDocumentHistory";
import { defaultDocument } from "@/lib/blog-document";
import { cn } from "@/lib/cn";

export function BlogDesignWorkspace() {
  const studio = useBlogStudio();
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [leftTab, setLeftTab] = useState<"blocks" | "templates" | "reusable">("templates");

  const { document: contentDoc, setDocument, setDragActive } = useDocumentHistory(
    studio.contentDocument ?? defaultDocument(),
  );

  const emitChange = (doc: typeof contentDoc) => {
    setDocument(doc);
    studio.setContentDocument(doc);
  };

  const selectedBlock = selectedBlockId ? findBlockById(contentDoc.blocks, selectedBlockId) : null;

  return (
    <div className="flex min-h-0 flex-1">
      {/* Left: Library */}
      <aside className="w-60 shrink-0 border-r border-border bg-card flex flex-col overflow-hidden">
        <div className="flex border-b border-border text-xs">
          {(["templates", "reusable"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              className={cn(
                "flex-1 py-2 capitalize",
                leftTab === tab ? "border-b-2 border-primary text-primary" : "text-muted-foreground",
              )}
              onClick={() => setLeftTab(tab)}
            >
              {tab === "reusable" ? "Saved" : "Templates"}
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-y-auto">
          {leftTab === "templates" ? (
            <BlogTemplateLibrary onApply={(doc) => emitChange(doc)} />
          ) : (
            <BlogReusableSectionsPanel document={contentDoc} onChange={emitChange} />
          )}
        </div>
      </aside>

      {/* Center: Layout canvas */}
      <main className="flex-1 min-w-0 overflow-y-auto">
        <BlogLayoutManager
          document={contentDoc}
          onChange={emitChange}
          selectedBlockId={selectedBlockId}
          onSelectBlock={setSelectedBlockId}
          onDragActive={setDragActive}
          devicePreview="desktop"
        />
      </main>

      {/* Right: Block inspector */}
      <aside
        className={cn(
          "shrink-0 border-l border-border bg-card flex flex-col overflow-y-auto transition-all duration-200",
          selectedBlock ? "w-72" : "w-72",
        )}
      >
        <div className="border-b border-border p-3 text-xs font-medium text-muted-foreground">
          {selectedBlock ? "Block settings" : "Inspector"}
        </div>
        {selectedBlock ? (
          <BlogBlockSettings
            block={selectedBlock}
            onChange={(id, patch) =>
              emitChange({
                ...contentDoc,
                blocks: updateBlockInTree(contentDoc.blocks, id, (b) => ({
                  ...b,
                  ...patch,
                  props: { ...b.props, ...patch.props },
                  content: patch.content ? { ...b.content, ...patch.content } : b.content,
                })),
              })
            }
          />
        ) : (
          <div className="p-4 text-sm text-muted-foreground">
            Select a block to edit its settings.
          </div>
        )}
      </aside>
    </div>
  );
}
