"use client";

import { useCallback, useRef, useState } from "react";

import type { BlogContentDocument } from "@/lib/blog-document";
import { cloneDocument } from "@/lib/blog-document";

const MAX_HISTORY = 50;

export type DocumentHistory = {
  past: BlogContentDocument[];
  future: BlogContentDocument[];
};

export function useDocumentHistory(initial: BlogContentDocument) {
  const [document, setDocumentState] = useState(initial);
  const historyRef = useRef<DocumentHistory>({ past: [], future: [] });
  const dragActiveRef = useRef(false);

  const setDocument = useCallback(
    (next: BlogContentDocument | ((prev: BlogContentDocument) => BlogContentDocument), opts?: { skipHistory?: boolean }) => {
      setDocumentState((prev) => {
        const resolved = typeof next === "function" ? next(prev) : next;
        if (!opts?.skipHistory && !dragActiveRef.current) {
          const h = historyRef.current;
          h.past = [...h.past.slice(-MAX_HISTORY + 1), cloneDocument(prev)];
          h.future = [];
        }
        return resolved;
      });
    },
    [],
  );

  const undo = useCallback(() => {
    const h = historyRef.current;
    if (!h.past.length) return;
    setDocumentState((current) => {
      const prev = h.past[h.past.length - 1];
      h.past = h.past.slice(0, -1);
      h.future = [cloneDocument(current), ...h.future];
      return cloneDocument(prev);
    });
  }, []);

  const redo = useCallback(() => {
    const h = historyRef.current;
    if (!h.future.length) return;
    setDocumentState((current) => {
      const next = h.future[0];
      h.future = h.future.slice(1);
      h.past = [...h.past, cloneDocument(current)];
      return cloneDocument(next);
    });
  }, []);

  const canUndo = historyRef.current.past.length > 0;
  const canRedo = historyRef.current.future.length > 0;

  const setDragActive = useCallback((active: boolean) => {
    dragActiveRef.current = active;
  }, []);

  const checkpoint = useCallback(() => {
    historyRef.current.past = [
      ...historyRef.current.past.slice(-MAX_HISTORY + 1),
      cloneDocument(document),
    ];
  }, [document]);

  return {
    document,
    setDocument,
    undo,
    redo,
    canUndo,
    canRedo,
    setDragActive,
    checkpoint,
  };
}
