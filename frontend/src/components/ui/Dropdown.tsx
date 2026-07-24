"use client";

import { type ReactNode, useEffect, useId, useLayoutEffect, useRef, useState } from "react";

import { cn } from "@/lib/cn";

import { Button } from "./Button";

export type DropdownItem = {
  id: string;
  label: string;
  onSelect: () => void;
  danger?: boolean;
  disabled?: boolean;
};

export function Dropdown({
  label,
  items,
  align = "right",
  className = "",
  menuPlacement = "auto",
}: {
  label: ReactNode;
  items: DropdownItem[];
  align?: "left" | "right";
  className?: string;
  /** Prefer opening above the trigger when space below is tight (e.g. ticket cards). */
  menuPlacement?: "auto" | "top" | "bottom";
}) {
  const [open, setOpen] = useState(false);
  const [openUpward, setOpenUpward] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useLayoutEffect(() => {
    if (!open || !root.current) return;
    if (menuPlacement === "top") {
      setOpenUpward(true);
      return;
    }
    if (menuPlacement === "bottom") {
      setOpenUpward(false);
      return;
    }
    const trigger = root.current.getBoundingClientRect();
    const menuHeight = menuRef.current?.offsetHeight ?? items.length * 44 + 8;
    const spaceBelow = window.innerHeight - trigger.bottom;
    const spaceAbove = trigger.top;
    setOpenUpward(spaceBelow < menuHeight + 12 && spaceAbove > spaceBelow);
  }, [open, items.length, menuPlacement]);

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
    <div ref={root} className={cn("relative inline-block", className)}>
      <Button
        variant="secondary"
        size="sm"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((v) => !v)}
      >
        {label}
        <span className="text-muted-foreground" aria-hidden>
          ▾
        </span>
      </Button>
      {open ? (
        <div
          ref={menuRef}
          id={menuId}
          role="menu"
          className={cn(
            "absolute z-30 min-w-[190px] overflow-hidden rounded-[var(--radius-md)] border border-border bg-popover py-1 text-popover-foreground shadow-[var(--shadow)]",
            openUpward ? "bottom-full mb-2" : "top-full mt-2",
            align === "right" ? "right-0" : "left-0",
          )}
        >
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              role="menuitem"
              disabled={item.disabled}
              className={cn(
                "block w-full px-3.5 py-2.5 text-left text-sm font-medium transition-colors",
                "focus-visible:bg-surface-muted focus-visible:outline-none",
                item.disabled
                  ? "cursor-not-allowed text-muted-foreground opacity-70"
                  : "hover:bg-surface-muted",
                item.danger && !item.disabled
                  ? "text-danger"
                  : !item.disabled
                    ? "text-popover-foreground"
                    : "",
              )}
              onClick={() => {
                if (item.disabled) return;
                item.onSelect();
                setOpen(false);
              }}
            >
              {item.label}
              {item.disabled ? (
                <span className="sr-only"> (unavailable)</span>
              ) : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
