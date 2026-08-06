"use client";

import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

import { AssistantLauncher } from "@/components/assistant/AssistantLauncher";
import { AssistantPanel } from "@/components/assistant/AssistantPanel";
import { useAssistantChat } from "@/components/assistant/hooks/useAssistantChat";
import { useAssistantOpenState } from "@/components/assistant/hooks/useAssistantOpenState";
import { useAuth } from "@/components/auth/AuthProvider";
import { useAnalytics } from "@/hooks/useAnalytics";
import {
  buildAssistantPageContext,
  resolveAssistantRole,
} from "@/lib/assistant/page-context";
import type { AssistantStatus } from "@/lib/types/assistant";
import { cn } from "@/lib/cn";

function useIsMobile(): boolean {
  const [mobile, setMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const update = () => setMobile(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return mobile;
}

export function PadeyaAssistantWidget({
  status,
}: {
  status: AssistantStatus;
}) {
  const { user } = useAuth();
  const pathname = usePathname() || "/";
  const { track } = useAnalytics();
  const isMobile = useIsMobile();
  const { isOpen, hydrated, open, close } = useAssistantOpenState();
  const [mounted, setMounted] = useState(false);

  const isAuthenticated = Boolean(user);
  const useCopilot =
    isAuthenticated && status.authenticated_enabled;

  const title = useCopilot
    ? status.product_authenticated || "Pàdéyá Copilot"
    : status.product_public || "Ask Pàdéyá";
  const subtitle = useCopilot
    ? "Navigate, understand and get things done"
    : "Find events, pages and answers";

  const role = resolveAssistantRole(user?.roles);
  const pageContext = useMemo(
    () =>
      buildAssistantPageContext({
        pathname,
        role: useCopilot ? role : null,
        pageTitle:
          typeof document !== "undefined" ? document.title : null,
      }),
    [pathname, role, useCopilot],
  );

  const {
    messages,
    streaming,
    statusPhase,
    online,
    sendMessage,
    stop,
    resetSession,
  } = useAssistantChat({
    pageContext,
    onMessageSent: () => {
      track("assistant_message_sent", {
        metadata: { mode: useCopilot ? "authenticated" : "public" },
      });
    },
  });

  useEffect(() => {
    setMounted(true);
  }, []);

  function handleOpen() {
    open();
    track("assistant_open", {
      metadata: { mode: useCopilot ? "authenticated" : "public" },
    });
  }

  function handleClose() {
    close();
    track("assistant_close", {
      metadata: { mode: useCopilot ? "authenticated" : "public" },
    });
  }

  function handleNewChat() {
    resetSession();
    track("assistant_new_chat", {
      metadata: { mode: useCopilot ? "authenticated" : "public" },
    });
  }

  if (!mounted || !hydrated) return null;

  const launcherLabel = useCopilot ? "Open Pàdéyá Copilot" : "Open Ask Pàdéyá";

  const shell = (
    <div
      className={cn(
        "pointer-events-none fixed z-50 flex flex-col items-end gap-3",
        // Stay clear of MobileBottomNav (~3.5rem + safe-area) on small screens
        "bottom-[calc(1rem+env(safe-area-inset-bottom))] right-3",
        "md:bottom-6 md:right-6",
        // Extra lift when personal bottom nav is likely present
        "max-md:bottom-[calc(4.75rem+env(safe-area-inset-bottom))]",
      )}
    >
      {isOpen ? (
        <div className="pointer-events-auto">
          {isMobile ? (
            <AssistantPanel
              title={title}
              subtitle={subtitle}
              online={online}
              messages={messages}
              role={useCopilot ? role : "public"}
              streaming={streaming}
              statusPhase={statusPhase}
              onSend={(msg) => void sendMessage(msg)}
              onStop={stop}
              onNewChat={handleNewChat}
              onClose={handleClose}
              mobileFullscreen
            />
          ) : (
            <AssistantPanel
              title={title}
              subtitle={subtitle}
              online={online}
              messages={messages}
              role={useCopilot ? role : "public"}
              streaming={streaming}
              statusPhase={statusPhase}
              onSend={(msg) => void sendMessage(msg)}
              onStop={stop}
              onNewChat={handleNewChat}
              onClose={handleClose}
            />
          )}
        </div>
      ) : (
        <div className="pointer-events-auto">
          <AssistantLauncher onClick={handleOpen} label={launcherLabel} />
        </div>
      )}
    </div>
  );

  return createPortal(shell, document.body);
}
