"use client";

import { type ReactNode, useState } from "react";

import { cn } from "@/lib/cn";

export type TabItem = {
  id: string;
  label: string;
  content: ReactNode;
};

export function Tabs({
  items,
  defaultId,
  activeId,
  onChange,
  className = "",
}: {
  items: TabItem[];
  defaultId?: string;
  /** Controlled active tab id */
  activeId?: string;
  onChange?: (id: string) => void;
  className?: string;
}) {
  const [internal, setInternal] = useState(defaultId ?? items[0]?.id);
  const active = activeId ?? internal;
  const current = items.find((t) => t.id === active) ?? items[0];

  function select(id: string) {
    if (activeId === undefined) setInternal(id);
    onChange?.(id);
  }

  return (
    <div className={cn("space-y-4", className)}>
      <div
        role="tablist"
        className="flex gap-1 overflow-x-auto rounded-[var(--radius-md)] border border-border bg-muted p-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {items.map((tab) => {
          const selected = tab.id === current?.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={selected}
              className={cn(
                "shrink-0 rounded-[calc(var(--radius-md)-2px)] px-3.5 py-2 text-sm font-semibold transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                selected
                  ? "bg-card text-heading shadow-[var(--shadow-soft)] ring-1 ring-border dark:bg-surface-elevated"
                  : "text-muted-foreground hover:bg-surface-inset hover:text-foreground",
              )}
              onClick={() => select(tab.id)}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      <div role="tabpanel">{current?.content}</div>
    </div>
  );
}
