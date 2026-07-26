"use client";

import { useEffect } from "react";

import { InstallPrompt } from "@/components/pwa/InstallPrompt";
import { OfflineBanner } from "@/components/pwa/OfflineBanner";

/**
 * Local `next dev` on localhost unregisters the SW so HMR isn't cache-fought.
 * HTTPS custom domains / tunnels (even under NODE_ENV=development) must register
 * `/sw.js` — browser push needs an active service worker + subscription.
 */
function shouldRegisterServiceWorker(): boolean {
  if (typeof window === "undefined") return false;
  if (!("serviceWorker" in navigator)) return false;
  if (process.env.NODE_ENV !== "development") return true;
  const host = window.location.hostname;
  const isLocal =
    host === "localhost" || host === "127.0.0.1" || host === "[::1]";
  return !isLocal && window.isSecureContext;
}

export function PwaProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!("serviceWorker" in navigator)) return;

    if (!shouldRegisterServiceWorker()) {
      void navigator.serviceWorker.getRegistrations().then((regs) => {
        for (const reg of regs) void reg.unregister();
      });
      return;
    }

    // Defer registration so SW work does not contend with first paint / hydration.
    const register = () => {
      void navigator.serviceWorker.register("/sw.js").catch(() => undefined);
    };
    const ric = window.requestIdleCallback?.bind(window);
    const cic = window.cancelIdleCallback?.bind(window);
    if (ric && cic) {
      const id = ric(register, { timeout: 4000 });
      return () => cic(id);
    }
    const t = setTimeout(register, 1500);
    return () => clearTimeout(t);
  }, []);

  return (
    <>
      <OfflineBanner />
      {children}
      <InstallPrompt />
    </>
  );
}
