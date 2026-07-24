import type { ReactNode } from "react";

import { MessagesMobileChrome } from "@/components/messaging/MessagesMobileChrome";

/** Placeholder height for the fixed `MessagesViewportFrame` (avoids footer jumping under the pane). */
export default function DashboardMessagesLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <MessagesMobileChrome>
      <div
        className="pointer-events-none min-h-[calc(100dvh-4rem-3.5rem-env(safe-area-inset-bottom))] md:min-h-[calc(100dvh-4.25rem-2.75rem)]"
        aria-hidden
      />
      {children}
    </MessagesMobileChrome>
  );
}
