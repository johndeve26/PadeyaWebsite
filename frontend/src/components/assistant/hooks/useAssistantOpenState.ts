"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "padeya_assistant_open";

export type AssistantOpenState = "closed" | "open" | "minimized";

function readStored(): AssistantOpenState {
  if (typeof window === "undefined") return "closed";
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (raw === "open" || raw === "minimized" || raw === "closed") return raw;
  } catch {
    // ignore
  }
  return "closed";
}

function writeStored(state: AssistantOpenState): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, state);
  } catch {
    // ignore
  }
}

/**
 * Open / minimized / closed — persisted in sessionStorage.
 * Never auto-opens on page load (starts closed unless user left it open).
 */
export function useAssistantOpenState() {
  const [state, setState] = useState<AssistantOpenState>("closed");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setState(readStored());
    setHydrated(true);
  }, []);

  const setOpenState = useCallback((next: AssistantOpenState) => {
    setState(next);
    writeStored(next);
  }, []);

  const open = useCallback(() => setOpenState("open"), [setOpenState]);
  const close = useCallback(() => setOpenState("closed"), [setOpenState]);
  const minimize = useCallback(() => setOpenState("minimized"), [setOpenState]);
  const toggle = useCallback(() => {
    setOpenState(state === "open" ? "closed" : "open");
  }, [setOpenState, state]);

  return {
    state,
    hydrated,
    isOpen: state === "open",
    isMinimized: state === "minimized",
    open,
    close,
    minimize,
    toggle,
    setOpenState,
  };
}
