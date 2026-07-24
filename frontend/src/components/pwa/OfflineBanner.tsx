"use client";

import { useOnlineStatus } from "@/lib/pwa/use-online-status";

export function OfflineBanner() {
  const online = useOnlineStatus();
  if (online) return null;

  return (
    <div
      role="status"
      className="sticky top-16 z-30 border-b border-paper/15 bg-ink px-4 py-2 text-center text-xs font-semibold text-primary sm:text-sm"
    >
      You’re offline — cached tickets may still open. Checkout, Vault, and payments need a connection.
    </div>
  );
}
