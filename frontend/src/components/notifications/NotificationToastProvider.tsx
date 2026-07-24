"use client";

import type { ReactNode } from "react";

import { NotificationPopupBridge } from "@/components/notifications/NotificationPopupBridge";
import { UiSoundUnlock } from "@/components/notifications/UiSoundUnlock";
import { ToastProvider } from "@/components/ui/Toast";

/**
 * In-app toast channel (Channel A) — wraps toast UI + popup polling bridge.
 * Does not request browser push permission.
 */
export function NotificationToastProvider({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      <UiSoundUnlock />
      <NotificationPopupBridge />
      {children}
    </ToastProvider>
  );
}
