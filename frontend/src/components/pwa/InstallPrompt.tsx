"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui";
import { detectPushDeviceContext, IOS_PUSH_HELPER } from "@/lib/push-device";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

const DISMISS_KEY = "padeya.pwa.install.dismissed";

/**
 * Optional install nudge.
 * - Chromium: uses beforeinstallprompt when available.
 * - iPhone/iPad: Home Screen app steps for push (all browsers; not Safari-only).
 */
export function InstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(
    null,
  );
  const [visible, setVisible] = useState(false);
  const [iosHint, setIosHint] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (localStorage.getItem(DISMISS_KEY) === "1") return;

    const device = detectPushDeviceContext();
    if (device.needsHomeScreenForPush) {
      queueMicrotask(() => {
        setIosHint(true);
        setVisible(true);
      });
      return;
    }

    const onPrompt = (event: Event) => {
      event.preventDefault();
      setDeferred(event as BeforeInstallPromptEvent);
      setVisible(true);
    };

    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  if (!visible) return null;
  if (!iosHint && !deferred) return null;

  return (
    <div className="fixed bottom-[4.75rem] left-3 right-3 z-50 mx-auto max-w-md rounded-xl border border-border bg-card p-4 shadow-[var(--shadow-strong)] md:bottom-6 md:left-auto md:right-6">
      <p className="text-sm font-bold text-foreground">
        {iosHint ? IOS_PUSH_HELPER.title : "Install Pàdéyá"}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        {iosHint
          ? `${IOS_PUSH_HELPER.body} ${IOS_PUSH_HELPER.browsersNote}`
          : "Add to your home screen for faster tickets and scanner access."}
      </p>
      <div className="mt-3 flex gap-2">
        {!iosHint && deferred ? (
          <Button
            size="sm"
            onClick={() => {
              void (async () => {
                await deferred.prompt();
                setVisible(false);
                setDeferred(null);
              })();
            }}
          >
            Install
          </Button>
        ) : null}
        <Button
          size="sm"
          variant={iosHint ? "secondary" : "ghost"}
          onClick={() => {
            localStorage.setItem(DISMISS_KEY, "1");
            setVisible(false);
          }}
        >
          {iosHint ? "Got it" : "Not now"}
        </Button>
      </div>
    </div>
  );
}
