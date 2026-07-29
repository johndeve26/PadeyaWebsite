"use client";
// BlogWriteWorkspace — Write tab: outline sidebar + editor canvas

import { useState } from "react";
import { useBlogStudio } from "@/components/blog/studio/BlogStudioProvider";
import {
  StandardBlogEditor,
  BlogOutlinePanel,
} from "@/components/blog/editor";
import { Input, Textarea } from "@/components/ui";
import { useWorkspaceDocument } from "@/components/blog/workspace/WorkspaceDocumentProvider";
import { cn } from "@/lib/cn";

type Props = {
  onAiAssistant: () => void;
};

export function BlogWriteWorkspace({ onAiAssistant: _onAiAssistant }: Props) {
  const studio = useBlogStudio();
  const { document: contentDoc, applyDocument } = useWorkspaceDocument();
  const [outlineOpen, setOutlineOpen] = useState(true);
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);

  return (
    <div className="flex min-h-0 flex-1" data-testid="blog-write-workspace">
      <aside
        className={cn(
          "hidden border-r border-border bg-card transition-all duration-200 overflow-y-auto md:block",
          outlineOpen ? "w-56 shrink-0" : "w-0 overflow-hidden",
        )}
      >
        <div className="p-3">
          <BlogOutlinePanel
            document={contentDoc}
            onNavigate={(id) => {
              setSelectedBlockId(id);
              document.getElementById(`block-${id}`)?.scrollIntoView({ behavior: "smooth" });
            }}
          />
        </div>
      </aside>

      <button
        type="button"
        className="hidden md:flex shrink-0 w-5 self-stretch items-center justify-center bg-surface/50 hover:bg-surface border-r border-border text-muted-foreground"
        onClick={() => setOutlineOpen((v) => !v)}
        title={outlineOpen ? "Collapse outline" : "Expand outline"}
      >
        <svg className="h-3 w-3" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path d={outlineOpen ? "M10 4L6 8l4 4" : "M6 4l4 4-4 4"} />
        </svg>
      </button>

      <main
        className="flex-1 min-w-0 overflow-y-auto"
        data-testid="blog-write-canvas"
      >
        <div className="mx-auto w-full max-w-4xl space-y-4 p-4 sm:p-6">
          <Input
            label="Title"
            value={studio.title}
            onChange={(e) => studio.patch({ title: e.target.value, dirty: true })}
            placeholder="Article title"
          />
          <Textarea
            label="Article summary"
            hint="Used on cards and listings — not the same as meta description."
            value={studio.excerpt}
            onChange={(e) => studio.patch({ excerpt: e.target.value, dirty: true })}
            rows={3}
          />
          <div className="min-w-[min(100%,30rem)]" data-testid="blog-editor-canvas">
            <StandardBlogEditor
              document={contentDoc}
              onChange={applyDocument}
              selectedBlockId={selectedBlockId}
              onSelectBlock={setSelectedBlockId}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
