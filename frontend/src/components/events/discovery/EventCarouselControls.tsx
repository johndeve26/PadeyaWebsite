"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function EventCarouselControls({
  onPrev,
  onNext,
  canPrev = true,
  canNext = true,
  label,
  className = "",
  tone = "dark",
}: {
  onPrev: () => void;
  onNext: () => void;
  canPrev?: boolean;
  canNext?: boolean;
  label: string;
  className?: string;
  tone?: "dark" | "light";
}) {
  const dark = tone === "dark";
  return (
    <div
      className={cn("flex items-center gap-2", className)}
      role="group"
      aria-label={`${label} controls`}
    >
      <ControlButton
        label={`Previous ${label}`}
        onClick={onPrev}
        disabled={!canPrev}
        dark={dark}
      >
        ←
      </ControlButton>
      <ControlButton
        label={`Next ${label}`}
        onClick={onNext}
        disabled={!canNext}
        dark={dark}
      >
        →
      </ControlButton>
    </div>
  );
}

function ControlButton({
  label,
  onClick,
  disabled,
  children,
  dark,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  children: ReactNode;
  dark: boolean;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex h-10 w-10 items-center justify-center rounded-full border text-base font-bold transition",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
        "disabled:pointer-events-none disabled:opacity-35",
        dark
          ? "border-paper/20 bg-paper/[0.06] text-paper hover:border-primary/50 hover:text-primary"
          : "border-border bg-card text-foreground hover:border-primary/40 hover:text-primary-text dark:bg-surface-elevated",
      )}
    >
      {children}
    </button>
  );
}
