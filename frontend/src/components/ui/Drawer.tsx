"use client";

import { type ReactNode, useEffect, useId, useState } from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/cn";

import { Button } from "./Button";

export type DrawerProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
};

/** Mobile-first bottom sheet; theme-safe overlay + elevated panel. */
export function Drawer({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  className = "",
}: DrawerProps) {
  const titleId = useId();
  const descId = useId();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open || !mounted) return null;

  const panel = (
    <div className="fixed inset-0 z-[100] flex items-end justify-center sm:items-center sm:p-4">
      <button
        type="button"
        aria-label="Close drawer"
        className="absolute inset-0 bg-[var(--overlay)] backdrop-blur-[2px]"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descId : undefined}
        className={cn(
          "relative z-10 flex max-h-[min(85dvh,920px)] w-full min-w-0 flex-col overflow-hidden rounded-t-[var(--radius-xl)] border border-border bg-popover text-popover-foreground shadow-[var(--shadow-strong)] sm:max-h-[min(92dvh,920px)] sm:max-w-lg sm:rounded-[var(--radius-xl)]",
          className,
        )}
      >
        <div className="flex shrink-0 items-start justify-between gap-4 border-b border-border px-4 py-4 sm:px-6">
          <div className="min-w-0 space-y-1">
            <h2
              id={titleId}
              className="text-balance text-lg font-extrabold tracking-tight text-heading"
            >
              {title}
            </h2>
            {description ? (
              <p
                id={descId}
                className="text-pretty text-sm leading-relaxed text-muted-foreground"
              >
                {description}
              </p>
            ) : null}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            aria-label="Close"
            className="h-9 w-9 shrink-0 px-0"
          >
            ✕
          </Button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:px-6 sm:pb-4">
          {children}
        </div>
        {footer ? (
          <div className="shrink-0 border-t border-border px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:px-6 sm:pb-3">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  );

  return createPortal(panel, document.body);
}
