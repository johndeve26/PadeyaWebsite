"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, type ReactNode } from "react";

import { useDocumentHistory } from "@/components/blog/editor/useDocumentHistory";
import { useBlogStudio } from "@/components/blog/studio/BlogStudioProvider";
import { useBlogStudioAutosave } from "@/components/blog/studio/useBlogStudioAutosave";
import { defaultDocument, type BlogContentDocument } from "@/lib/blog-document";

type WorkspaceDocumentContextValue = {
  document: BlogContentDocument;
  setDocument: (
    next: BlogContentDocument | ((prev: BlogContentDocument) => BlogContentDocument),
    opts?: { skipHistory?: boolean },
  ) => void;
  applyDocument: (doc: BlogContentDocument, opts?: { skipHistory?: boolean }) => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  setDragActive: (active: boolean) => void;
  saveNow: () => Promise<void>;
};

const WorkspaceDocumentContext = createContext<WorkspaceDocumentContextValue | null>(null);

export function WorkspaceDocumentProvider({ children }: { children: ReactNode }) {
  const studio = useBlogStudio();
  const {
    document,
    setDocument: setHistoryDocument,
    undo,
    redo,
    canUndo,
    canRedo,
    setDragActive,
  } = useDocumentHistory(studio.contentDocument ?? defaultDocument());

  const contentVersionRef = useRef(studio.contentVersion);
  const documentRef = useRef(document);
  documentRef.current = document;

  useEffect(() => {
    if (studio.contentVersion === contentVersionRef.current) return;
    contentVersionRef.current = studio.contentVersion;
    if (studio.contentDocument) {
      setHistoryDocument(studio.contentDocument, { skipHistory: true });
    }
  }, [studio.contentDocument, studio.contentVersion, setHistoryDocument]);

  const applyDocument = useCallback(
    (doc: BlogContentDocument, opts?: { skipHistory?: boolean }) => {
      setHistoryDocument(doc, opts);
      studio.setContentDocument(doc);
      studio.patch({ dirty: true });
    },
    [setHistoryDocument, studio],
  );

  const setDocument = useCallback(
    (
      next: BlogContentDocument | ((prev: BlogContentDocument) => BlogContentDocument),
      opts?: { skipHistory?: boolean },
    ) => {
      const resolved =
        typeof next === "function" ? next(documentRef.current) : next;
      setHistoryDocument(resolved, opts);
      studio.setContentDocument(resolved);
      studio.patch({ dirty: true });
    },
    [setHistoryDocument, studio],
  );

  const { saveNow } = useBlogStudioAutosave({ enabled: true });

  const value = useMemo(
    () => ({
      document,
      setDocument,
      applyDocument,
      undo,
      redo,
      canUndo,
      canRedo,
      setDragActive,
      saveNow,
    }),
    [
      document,
      setDocument,
      applyDocument,
      undo,
      redo,
      canUndo,
      canRedo,
      setDragActive,
      saveNow,
    ],
  );

  return (
    <WorkspaceDocumentContext.Provider value={value}>
      {children}
    </WorkspaceDocumentContext.Provider>
  );
}

export function useWorkspaceDocument() {
  const ctx = useContext(WorkspaceDocumentContext);
  if (!ctx) {
    throw new Error("useWorkspaceDocument must be used within WorkspaceDocumentProvider");
  }
  return ctx;
}
