"use client";
// BlogDesignWorkspace — Design tab: library panel + layout canvas + block inspector

import { useState } from "react";
import {
  BlogLayoutManager,
  BlogBlockSettings,
  BlogTemplateLibrary,
  BlogReusableSectionsPanel,
} from "@/components/blog/editor";
import { findBlockById, updateBlockInTree } from "@/lib/blog-document";
import { useWorkspaceDocument } from "@/components/blog/workspace/WorkspaceDocumentProvider";
import { cn } from "@/lib/cn";

export function BlogDesignWorkspace() {
  const { document: contentDoc, applyDocument, setDragActive } = useWorkspaceDocument();
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [leftTab, setLeftTab] = useState<"templates" | "reusable">("templates");

  const selectedBlock = selectedBlockId ? findBlockById(contentDoc.blocks, selectedBlockId) : null;

  return (
    <div className="flex min-h-0 flex-1" data-testid="blog-design-workspace">
      <aside className="hidden w-60 shrink-0 min-h-0 border-r border-border bg-card flex-col overflow-hidden md:flex">
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
            <BlogTemplateLibrary onApply={(doc) => applyDocument(doc)} />
          ) : (
            <BlogReusableSectionsPanel document={contentDoc} onChange={applyDocument} />
          )}
        </div>
      </aside>

      <main className="flex-1 min-h-0 min-w-[min(100%,30rem)] overflow-y-auto" data-testid="blog-design-canvas">
        <BlogLayoutManager
          document={contentDoc}
          onChange={applyDocument}
          selectedBlockId={selectedBlockId}
          onSelectBlock={setSelectedBlockId}
          onDragActive={setDragActive}
          devicePreview="desktop"
        />
      </main>

      <aside
        className={cn(
          "hidden shrink-0 min-h-0 border-l border-border bg-card flex-col overflow-y-auto lg:flex",
          selectedBlock ? "w-72" : "w-56",
        )}
      >
        <div className="border-b border-border p-3 text-xs font-medium text-muted-foreground">
          {selectedBlock ? "Block settings" : "Inspector"}
        </div>
        {selectedBlock ? (
          <BlogBlockSettings
            block={selectedBlock}
            onChange={(id, patch) =>
              applyDocument({
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
