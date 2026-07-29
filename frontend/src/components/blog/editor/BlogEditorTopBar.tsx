"use client";

import { Button } from "@/components/ui";
import type { EditorMode, PreviewDevice, PreviewTheme } from "@/lib/blog-document";
import type { AutosaveStatus } from "@/components/blog/studio/types";

type Props = {
  editorMode: EditorMode;
  onEditorModeChange: (mode: EditorMode) => void;
  onUndo: () => void;
  onRedo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  onPreview: () => void;
  onSave: () => void;
  onPublish: () => void;
  autosaveStatus: AutosaveStatus;
  devicePreview: PreviewDevice;
  onDevicePreviewChange: (d: PreviewDevice) => void;
  themePreview: PreviewTheme;
  onThemePreviewChange: (t: PreviewTheme) => void;
  distractionFree: boolean;
  onDistractionFreeToggle: () => void;
};

export function BlogEditorTopBar({
  editorMode,
  onEditorModeChange,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  onPreview,
  onSave,
  onPublish,
  autosaveStatus,
  devicePreview,
  onDevicePreviewChange,
  themePreview,
  onThemePreviewChange,
  distractionFree,
  onDistractionFreeToggle,
}: Props) {
  const saveLabel =
    autosaveStatus === "saving"
      ? "Saving…"
      : autosaveStatus === "saved"
        ? "Saved"
        : autosaveStatus === "failed"
          ? "Save failed"
          : autosaveStatus === "conflict"
            ? "Conflict"
            : "Save";

  return (
    <header className="sticky top-0 z-20 flex flex-wrap items-center gap-2 border-b border-border bg-surface/95 px-4 py-2 backdrop-blur">
      <div className="flex rounded-[var(--radius-md)] border border-border overflow-hidden">
        <button
          type="button"
          className={`px-3 py-1.5 text-sm ${editorMode === "standard" ? "bg-primary text-primary-foreground" : "hover:bg-muted/40"}`}
          onClick={() => onEditorModeChange("standard")}
        >
          Standard Editor
        </button>
        <button
          type="button"
          className={`px-3 py-1.5 text-sm ${editorMode === "layout" ? "bg-primary text-primary-foreground" : "hover:bg-muted/40"}`}
          onClick={() => onEditorModeChange("layout")}
        >
          Layout Manager
        </button>
      </div>

      <div className="flex items-center gap-1">
        <Button type="button" variant="ghost" size="sm" onClick={onUndo} disabled={!canUndo}>
          Undo
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={onRedo} disabled={!canRedo}>
          Redo
        </Button>
      </div>

      <div className="flex items-center gap-1 ml-auto">
        <select
          className="text-sm rounded-[var(--radius-md)] border border-border bg-surface px-2 py-1"
          value={devicePreview}
          onChange={(e) => onDevicePreviewChange(e.target.value as PreviewDevice)}
          aria-label="Device preview"
        >
          <option value="desktop">Desktop</option>
          <option value="tablet">Tablet</option>
          <option value="mobile">Mobile</option>
        </select>
        <select
          className="text-sm rounded-[var(--radius-md)] border border-border bg-surface px-2 py-1"
          value={themePreview}
          onChange={(e) => onThemePreviewChange(e.target.value as PreviewTheme)}
          aria-label="Theme preview"
        >
          <option value="system">System</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
        <Button type="button" variant="ghost" size="sm" onClick={onDistractionFreeToggle}>
          {distractionFree ? "Exit focus" : "Focus"}
        </Button>
        <Button type="button" variant="secondary" size="sm" onClick={onPreview}>
          Preview
        </Button>
        <Button type="button" variant="secondary" size="sm" onClick={onSave}>
          {saveLabel}
        </Button>
        <Button type="button" size="sm" onClick={onPublish}>
          Publish
        </Button>
      </div>
    </header>
  );
}
