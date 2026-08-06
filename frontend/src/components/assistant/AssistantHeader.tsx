"use client";

import { useEffect, useId, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

export function AssistantHeader({
  title,
  subtitle,
  online,
  onNewChat,
  onClose,
}: {
  title: string;
  subtitle: string;
  online: boolean;
  onNewChat: () => void;
  onClose: () => void;
}) {
  const titleId = useId();
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!privacyOpen) return;
    function onDoc(e: MouseEvent) {
      if (!menuRef.current?.contains(e.target as Node)) {
        setPrivacyOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [privacyOpen]);

  return (
    <header className="shrink-0 border-b border-border">
      <div className="flex items-start justify-between gap-2 px-4 py-3 sm:gap-3 sm:px-5">
        <div className="min-w-0 flex-1 space-y-0.5">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <h2
              id={titleId}
              className="text-base font-extrabold leading-tight tracking-tight text-heading"
            >
              {title}
            </h2>
            <span
              className={cn(
                "inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
                online
                  ? "bg-primary/15 text-primary-text"
                  : "bg-surface-muted text-muted-foreground",
              )}
              title={online ? "Online" : "Offline"}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  online ? "bg-primary" : "bg-muted-foreground",
                )}
                aria-hidden
              />
              {online ? "Online" : "Offline"}
            </span>
          </div>
          <p className="text-xs leading-snug text-muted-foreground">{subtitle}</p>
        </div>

        <div className="flex shrink-0 items-center gap-0.5 sm:gap-1" ref={menuRef}>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            aria-haspopup="dialog"
            aria-expanded={privacyOpen}
            aria-controls={privacyOpen ? `${titleId}-privacy` : undefined}
            aria-label="Privacy information"
            onClick={() => setPrivacyOpen((v) => !v)}
            className="px-2 text-xs sm:px-2.5 sm:text-sm"
          >
            Privacy
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            aria-label="New chat"
            onClick={onNewChat}
            className="px-2 text-xs sm:px-2.5 sm:text-sm"
          >
            New
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            aria-label="Close assistant"
            onClick={onClose}
            className="px-2 text-xs sm:px-2.5 sm:text-sm"
          >
            Close
          </Button>
        </div>
      </div>

      {privacyOpen ? (
        <div
          id={`${titleId}-privacy`}
          role="dialog"
          aria-label="Privacy information"
          className="border-t border-border bg-surface-muted/40 px-4 py-3 text-xs sm:px-5"
        >
          <p className="font-semibold text-heading">Privacy</p>
          <p className="mt-1.5 leading-relaxed text-muted-foreground">
            Conversations may include the page you are on (route only — no
            passwords or payment details). Do not paste secrets. You can start a
            new chat anytime.
          </p>
        </div>
      ) : null}
    </header>
  );
}
