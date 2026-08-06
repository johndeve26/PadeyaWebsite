"use client";

import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  fetchAssistantStatus,
  isAssistantVisibleForUser,
} from "@/lib/assistant-api";
import { shouldHideAssistant } from "@/lib/assistant/checkout-guard";
import type { AssistantStatus } from "@/lib/types/assistant";

/**
 * Thin shell: path guard + status fetch, then lazy-load the chat bundle.
 * Mounted from root layout — keeps the homepage free of the full assistant code.
 */
const PadeyaAssistantWidget = dynamic(
  () =>
    import("@/components/assistant/PadeyaAssistantWidget").then(
      (m) => m.PadeyaAssistantWidget,
    ),
  { ssr: false },
);

export function PadeyaAssistantLoader() {
  const pathname = usePathname();
  const { user, authInitialized } = useAuth();
  const [status, setStatus] = useState<AssistantStatus | null>(null);
  const [ready, setReady] = useState(false);

  const hiddenByPath = shouldHideAssistant(pathname);

  useEffect(() => {
    if (hiddenByPath) {
      setReady(false);
      return;
    }
    if (!authInitialized) return;

    const controller = new AbortController();
    let cancelled = false;

    void (async () => {
      try {
        const next = await fetchAssistantStatus(controller.signal);
        if (cancelled) return;
        setStatus(next);
        setReady(true);
      } catch {
        if (!cancelled) {
          setStatus(null);
          setReady(false);
        }
      }
    })();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [authInitialized, hiddenByPath, pathname]);

  if (hiddenByPath || !ready || !status) return null;
  if (!isAssistantVisibleForUser(status, Boolean(user))) return null;

  return <PadeyaAssistantWidget status={status} />;
}
