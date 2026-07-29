"use client";

import { useCallback, useEffect, useState } from "react";

import { BlogEditorTopBar } from "@/components/blog/editor/BlogEditorTopBar";
import { BlogLayoutManager } from "@/components/blog/editor/BlogLayoutManager";
import { BlogBlockSettings } from "@/components/blog/editor/BlogBlockSettings";
import { BlogOutlinePanel } from "@/components/blog/editor/BlogOutlinePanel";
import { BlogReusableSectionsPanel } from "@/components/blog/editor/BlogReusableSectionsPanel";
import { BlogResponsivePreview } from "@/components/blog/editor/BlogResponsivePreview";
import { BlogTemplateLibrary } from "@/components/blog/editor/BlogTemplateLibrary";
import { StandardBlogEditor } from "@/components/blog/editor/StandardBlogEditor";
import { useDocumentHistory } from "@/components/blog/editor/useDocumentHistory";
import { BlogCreationEntry, type CreationChoice } from "@/components/blog/editor/BlogCreationEntry";
import { useToast } from "@/components/ui";
import type { AutosaveStatus } from "@/components/blog/studio/types";
import {
  cloneDocument,
  defaultDocument,
  findBlockById,
  updateBlockInTree,
  type BlogContentDocument,
  type EditorMode,
  type HeroSettings,
  type PreviewDevice,
  type PreviewTheme,
} from "@/lib/blog-document";

type Props = {
  postId: string | null;
  title: string;
  excerpt: string;
  bodyHtml?: string | null;
  initialDocument?: BlogContentDocument | null;
  initialEditorMode?: EditorMode | null;
  initialHeroSettings?: HeroSettings | null;
  contentVersion: number;
  autosaveStatus: AutosaveStatus;
  isNew: boolean;
  showAiPanel?: boolean;
  onDocumentChange: (doc: BlogContentDocument, meta: { editorMode: EditorMode }) => void;
  onManualSave: () => void;
  onPublish: () => void;
  onAiBlock?: (blockId: string) => void;
  onCreationStarted?: (choice: CreationChoice) => void;
  aiPanel?: React.ReactNode;
  seoPanel?: React.ReactNode;
  publishPanel?: React.ReactNode;
};

export function BlogEditorShell({
  postId,
  title,
  excerpt,
  bodyHtml,
  initialDocument,
  initialEditorMode,
  contentVersion,
  autosaveStatus,
  isNew,
  onDocumentChange,
  onManualSave,
  onPublish,
  onAiBlock,
  onCreationStarted,
  aiPanel,
  seoPanel,
  publishPanel,
}: Props) {
  const toast = useToast();
  const [creationDone, setCreationDone] = useState(!isNew);
  const [editorMode, setEditorMode] = useState<EditorMode>(
    (initialEditorMode as EditorMode) || "standard",
  );
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [distractionFree, setDistractionFree] = useState(false);
  const [devicePreview, setDevicePreview] = useState<PreviewDevice>("desktop");
  const [themePreview, setThemePreview] = useState<PreviewTheme>("system");
  const [leftTab, setLeftTab] = useState<"outline" | "blocks" | "templates" | "sections">("outline");

  const {
    document: contentDoc,
    setDocument,
    undo,
    redo,
    canUndo,
    canRedo,
    setDragActive,
  } = useDocumentHistory(initialDocument || defaultDocument());

  useEffect(() => {
    if (initialDocument) {
      setDocument(initialDocument, { skipHistory: true });
    }
  }, [contentVersion]); // eslint-disable-line react-hooks/exhaustive-deps

  const emitChange = useCallback(
    (doc: BlogContentDocument) => {
      setDocument(doc);
      onDocumentChange(doc, { editorMode });
    },
    [editorMode, onDocumentChange, setDocument],
  );

  const handleCreation = (choice: CreationChoice, doc?: BlogContentDocument) => {
    if (doc) setDocument(doc, { skipHistory: true });
    setCreationDone(true);
    onCreationStarted?.(choice);
    if (choice === "ai") {
      toast.push({
        tone: "info",
        title: "AI workflow is optional — open the assistant when you want help.",
      });
    }
  };

  const selectedBlock = selectedBlockId
    ? findBlockById(contentDoc.blocks, selectedBlockId)
    : null;

  if (isNew && !creationDone) {
    return <BlogCreationEntry onContinue={handleCreation} />;
  }

  return (
    <div className="flex min-h-[70vh] flex-col">
      <BlogEditorTopBar
        editorMode={editorMode}
        onEditorModeChange={(m) => {
          setEditorMode(m);
          onDocumentChange(contentDoc, { editorMode: m });
        }}
        onUndo={undo}
        onRedo={redo}
        canUndo={canUndo}
        canRedo={canRedo}
        onPreview={() => setPreviewOpen((v) => !v)}
        onSave={onManualSave}
        onPublish={onPublish}
        autosaveStatus={autosaveStatus}
        devicePreview={devicePreview}
        onDevicePreviewChange={setDevicePreview}
        themePreview={themePreview}
        onThemePreviewChange={setThemePreview}
        distractionFree={distractionFree}
        onDistractionFreeToggle={() => setDistractionFree((v) => !v)}
      />

      <div className="flex flex-1 min-h-0">
        {!distractionFree ? (
          <aside className="hidden lg:flex w-56 shrink-0 flex-col border-r border-border bg-surface/50">
            <div className="flex border-b border-border text-xs">
              {(["outline", "templates", "sections"] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  className={`flex-1 py-2 capitalize ${leftTab === tab ? "border-b-2 border-primary" : "text-muted-foreground"}`}
                  onClick={() => setLeftTab(tab)}
                >
                  {tab}
                </button>
              ))}
            </div>
            {leftTab === "outline" ? (
              <BlogOutlinePanel
                document={contentDoc}
                onNavigate={(id) => {
                  setSelectedBlockId(id);
                  document.getElementById(`block-${id}`)?.scrollIntoView({ behavior: "smooth" });
                }}
              />
            ) : null}
            {leftTab === "templates" ? (
              <BlogTemplateLibrary onApply={(doc) => emitChange(doc)} />
            ) : null}
            {leftTab === "sections" ? (
              <BlogReusableSectionsPanel document={contentDoc} onChange={emitChange} />
            ) : null}
          </aside>
        ) : null}

        <main className="flex-1 overflow-y-auto min-w-0">
          {previewOpen ? (
            <div className="p-6">
              <BlogResponsivePreview
                document={contentDoc}
                title={title}
                excerpt={excerpt}
                device={devicePreview}
                theme={themePreview}
                bodyHtml={bodyHtml}
              />
            </div>
          ) : editorMode === "layout" ? (
            <BlogLayoutManager
              document={contentDoc}
              onChange={emitChange}
              selectedBlockId={selectedBlockId}
              onSelectBlock={setSelectedBlockId}
              onDragActive={setDragActive}
              onAiBlock={onAiBlock}
              devicePreview={devicePreview}
            />
          ) : (
            <StandardBlogEditor
              document={contentDoc}
              onChange={emitChange}
              selectedBlockId={selectedBlockId}
              onSelectBlock={setSelectedBlockId}
              onAiBlock={onAiBlock}
              distractionFree={distractionFree}
            />
          )}
        </main>

        {!distractionFree ? (
          <aside className="hidden xl:flex w-72 shrink-0 flex-col border-l border-border bg-surface/50 overflow-y-auto">
            <div className="border-b border-border p-2 text-xs font-medium">Block settings</div>
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
            {seoPanel ? (
              <>
                <div className="border-t border-border p-2 text-xs font-medium">SEO</div>
                {seoPanel}
              </>
            ) : null}
            {publishPanel ? (
              <>
                <div className="border-t border-border p-2 text-xs font-medium">Publish</div>
                {publishPanel}
              </>
            ) : null}
          </aside>
        ) : null}
      </div>

      {!distractionFree && aiPanel ? (
        <div className="border-t border-border">{aiPanel}</div>
      ) : null}
    </div>
  );
}
