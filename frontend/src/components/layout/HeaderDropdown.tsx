"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";

import { cn } from "@/lib/cn";

import {
  isAdminPath,
  isHostWorkspacePath,
  isPersonalPath,
} from "./headerNav";

export type HeaderMenuItem = {
  id: string;
  label: string;
  href?: string;
  onSelect?: () => void;
  danger?: boolean;
};

function MenuPanel({
  id,
  open,
  align,
  items,
  onClose,
}: {
  id: string;
  open: boolean;
  align: "left" | "right";
  items: HeaderMenuItem[];
  onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div
      id={id}
      role="menu"
      className={cn(
        "absolute z-50 mt-2 min-w-[220px] overflow-hidden rounded-[var(--radius-md)] border border-border bg-popover py-1.5 text-popover-foreground shadow-[var(--shadow)]",
        align === "right" ? "right-0" : "left-0",
      )}
    >
      {items.map((item) => {
        const className = cn(
          "block w-full px-3.5 py-2.5 text-left text-sm font-semibold transition-colors",
          "focus-visible:bg-surface-muted focus-visible:outline-none",
          item.danger
            ? "text-danger hover:bg-surface-muted"
            : "text-popover-foreground hover:bg-surface-muted",
        );
        if (item.href) {
          return (
            <Link
              key={item.id}
              href={item.href}
              role="menuitem"
              className={className}
              onClick={onClose}
            >
              {item.label}
            </Link>
          );
        }
        return (
          <button
            key={item.id}
            type="button"
            role="menuitem"
            className={className}
            onClick={() => {
              item.onSelect?.();
              onClose();
            }}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

export function HeaderDropdown({
  label,
  ariaLabel,
  items,
  align = "right",
  active = false,
  className = "",
  tone = "default",
}: {
  label: React.ReactNode;
  ariaLabel: string;
  items: HeaderMenuItem[];
  align?: "left" | "right";
  active?: boolean;
  className?: string;
  tone?: "default" | "onDark";
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={root} className={cn("relative inline-flex", className)}>
      <button
        type="button"
        className={cn(
          "inline-flex h-10 items-center gap-1.5 rounded-[var(--radius-sm)] px-2.5 text-sm font-semibold transition-colors sm:px-3",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2",
          tone === "onDark"
            ? cn(
                "focus-visible:ring-offset-ink",
                active
                  ? "bg-paper text-ink"
                  : "text-paper/85 hover:bg-paper/10 hover:text-paper",
              )
            : cn(
                "focus-visible:ring-offset-background",
                active
                  ? "bg-ink text-paper"
                  : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
              ),
        )}
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="inline-flex shrink-0 items-center justify-center">
          {label}
        </span>
        <span className="text-[0.65rem] opacity-70" aria-hidden>
          ▾
        </span>
      </button>
      <MenuPanel
        id={menuId}
        open={open}
        align={align}
        items={items}
        onClose={() => setOpen(false)}
      />
    </div>
  );
}

export function workspaceMenuActive(
  pathname: string,
  mode: "personal" | "host" | "admin",
): boolean {
  if (mode === "personal") return isPersonalPath(pathname);
  if (mode === "host") return isHostWorkspacePath(pathname);
  return isAdminPath(pathname);
}
