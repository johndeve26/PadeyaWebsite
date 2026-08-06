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
    <header className="flex shrink-0 items-start justify-between gap-3 border-b border-border px-4 py-3 sm:px-5">
      <div className="min-w-0 space-y-0.5">
        <div className="flex items-center gap-2">
          <h2
            id={titleId}
            className="truncate text-base font-extrabold tracking-tight text-heading"
          >
            {title}
          </h2>
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
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
        <p className="truncate text-xs text-muted-foreground">{subtitle}</p>
      </div>

      <div className="flex shrink-0 items-center gap-1">
        <div className="relative" ref={menuRef}>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            aria-haspopup="menu"
            aria-expanded={privacyOpen}
            aria-label="Privacy information"
            onClick={() => setPrivacyOpen((v) => !v)}
            className="px-2.5"
          >
            Privacy
          </Button>
          {privacyOpen ? (
            <div
              role="menu"
              className="absolute right-0 z-20 mt-1 w-64 rounded-[var(--radius-md)] border border-border bg-popover p-3 text-xs text-popover-foreground shadow-[var(--shadow)]"
            >
              <p className="font-semibold text-heading">Privacy</p>
              <p className="mt-1.5 leading-relaxed text-muted-foreground">
                Conversations may include the page you are on (route only — no
                passwords or payment details). Do not paste secrets. You can
                start a new chat anytime.
              </p>
            </div>
          ) : null}
        </div>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          aria-label="New chat"
          onClick={onNewChat}
          className="px-2.5"
        >
          New
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          aria-label="Close assistant"
          onClick={onClose}
          className="px-2.5"
        >
          Close
        </Button>
      </div>
    </header>
  );
}
