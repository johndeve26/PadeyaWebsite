"use client";
// BlogWriteWorkspace — Write tab: outline sidebar + editor canvas + AI drawer

import { useState, useCallback } from "react";
import { useBlogStudio } from "@/components/blog/studio/BlogStudioProvider";
import { useBlogStudioAutosave } from "@/components/blog/studio/useBlogStudioAutosave";
import { BlogEditorShell } from "@/components/blog/editor";
import { cn } from "@/lib/cn";
import type { BlogContentDocument } from "@/lib/blog-document";

type Props = {
  onAiAssistant: () => void;
};

export function BlogWriteWorkspace({ onAiAssistant: _onAiAssistant }: Props) {
  const studio = useBlogStudio();
  const [outlineOpen, setOutlineOpen] = useState(true);
  const { saveNow } = useBlogStudioAutosave({ enabled: true });

  const handleDocumentChange = useCallback(
    (doc: BlogContentDocument, meta: { editorMode: import("@/lib/blog-document").EditorMode }) => {
      studio.setContentDocument(doc);
      studio.patch({ editorMode: meta.editorMode, dirty: true });
    },
    [studio],
  );

  return (
    <div className="flex min-h-0 flex-1">
      {/* Left: Outline sidebar */}
      <aside
        className={cn(
          "border-r border-border bg-card transition-all duration-200 overflow-y-auto",
          outlineOpen ? "w-56 shrink-0" : "w-0 overflow-hidden",
        )}
      >
        <div className="p-3 space-y-1">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Outline
          </p>
          {studio.outline.sections.length === 0 ? (
            <p className="text-xs text-muted-foreground">No outline sections.</p>
          ) : (
            <ol className="space-y-1">
              {studio.outline.sections.map((sec, i) => (
                <li key={sec.id}>
                  <button
                    type="button"
                    className="w-full text-left text-xs py-1 px-2 rounded hover:bg-surface/70 text-muted-foreground hover:text-foreground truncate"
                    title={sec.heading}
                  >
                    {i + 1}. {sec.heading}
                  </button>
                </li>
              ))}
            </ol>
          )}
        </div>
      </aside>

      {/* Outline collapse toggle */}
      <button
        type="button"
        className="shrink-0 w-5 self-stretch flex items-center justify-center bg-surface/50 hover:bg-surface border-r border-border text-muted-foreground"
        onClick={() => setOutlineOpen((v) => !v)}
        title={outlineOpen ? "Collapse outline" : "Expand outline"}
      >
        <svg className="h-3 w-3" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path d={outlineOpen ? "M10 4L6 8l4 4" : "M6 4l4 4-4 4"} />
        </svg>
      </button>

      {/* Center: Editor */}
      <main className="flex-1 min-w-0 min-w-[480px] overflow-y-auto">
        <BlogEditorShell
          postId={studio.postId}
          title={studio.title}
          excerpt={studio.excerpt}
          bodyHtml={studio.bodyHtml}
          initialDocument={studio.contentDocument}
          initialEditorMode={studio.editorMode}
          initialHeroSettings={studio.heroSettings}
          contentVersion={studio.contentVersion}
          autosaveStatus={studio.autosaveStatus}
          isNew={!studio.postId}
          onDocumentChange={handleDocumentChange}
          onManualSave={() => void saveNow()}
          onPublish={() => {
            // Publishing happens in Publish tab
          }}
        />
      </main>
    </div>
  );
}
