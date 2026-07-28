"use client";

import type { ReactNode } from "react";

import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";

export function BlogStudioShell({
  left,
  main,
  right,
  leftOpen,
  rightOpen,
  onToggleLeft,
  onToggleRight,
  className,
}: {
  left: ReactNode;
  main: ReactNode;
  right: ReactNode;
  leftOpen?: boolean;
  rightOpen?: boolean;
  onToggleLeft?: () => void;
  onToggleRight?: () => void;
  className?: string;
}) {
  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap gap-2 xl:hidden">
        <Button
          size="sm"
          variant="secondary"
          onClick={onToggleLeft}
          type="button"
        >
          {leftOpen ? "Hide brief" : "Brief & workflow"}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={onToggleRight}
          type="button"
        >
          {rightOpen ? "Hide publish" : "SEO & publish"}
        </Button>
      </div>

      <div className="grid gap-4 xl:grid-cols-[260px_minmax(0,1fr)_300px]">
        <aside
          className={cn(
            "min-w-0 space-y-4",
            leftOpen ? "block" : "hidden",
            "xl:block",
          )}
        >
          <div className="xl:sticky xl:top-24 xl:max-h-[calc(100vh-7rem)] xl:overflow-y-auto xl:pr-1">
            {left}
          </div>
        </aside>

        <section className="min-w-0 space-y-4">{main}</section>

        <aside
          className={cn(
            "min-w-0 space-y-4",
            rightOpen ? "block" : "hidden",
            "xl:block",
          )}
        >
          <div className="xl:sticky xl:top-24 xl:max-h-[calc(100vh-7rem)] xl:overflow-y-auto xl:pr-1">
            {right}
          </div>
        </aside>
      </div>
    </div>
  );
}

export function StudioPanel({
  title,
  description,
  children,
  actions,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="space-y-3 rounded-[var(--radius-md)] border border-border bg-surface px-3 py-3 shadow-[var(--shadow-soft)]">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-foreground">{title}</p>
          {description ? (
            <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
          ) : null}
        </div>
        {actions}
      </div>
      {children}
    </div>
  );
}
