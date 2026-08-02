"use client";

import {
  type ReactNode,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/cn";

import { Button } from "./Button";

export type DropdownItem = {
  id: string;
  label: string;
  onSelect: () => void;
  danger?: boolean;
  disabled?: boolean;
};

type MenuCoords = {
  top: number;
  left: number;
  minWidth: number;
  openUpward: boolean;
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
  const [coords, setCoords] = useState<MenuCoords | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useLayoutEffect(() => {
    if (!open || !root.current) {
      setCoords(null);
      return;
    }

    const place = () => {
      const trigger = root.current?.getBoundingClientRect();
      if (!trigger) return;

      const menuHeight = menuRef.current?.offsetHeight ?? items.length * 44 + 8;
      const menuWidth = Math.max(
        menuRef.current?.offsetWidth ?? 190,
        trigger.width,
        190,
      );
      const gap = 8;
      const spaceBelow = window.innerHeight - trigger.bottom;
      const spaceAbove = trigger.top;

      let openUpward = false;
      if (menuPlacement === "top") openUpward = true;
      else if (menuPlacement === "bottom") openUpward = false;
      else {
        openUpward = spaceBelow < menuHeight + gap && spaceAbove > spaceBelow;
      }

      const top = openUpward
        ? Math.max(8, trigger.top - gap - menuHeight)
        : Math.min(window.innerHeight - menuHeight - 8, trigger.bottom + gap);

      let left =
        align === "right" ? trigger.right - menuWidth : trigger.left;
      left = Math.min(Math.max(8, left), window.innerWidth - menuWidth - 8);

      setCoords({
        top,
        left,
        minWidth: menuWidth,
        openUpward,
      });
    };

    place();
    // Remeasure after paint so real menu height can flip if needed.
    const raf = window.requestAnimationFrame(place);
    return () => window.cancelAnimationFrame(raf);
  }, [open, items.length, menuPlacement, align]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      const target = e.target as Node;
      if (root.current?.contains(target)) return;
      if (menuRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onRepositionClose = () => setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", onRepositionClose);
    window.addEventListener("scroll", onRepositionClose, true);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onRepositionClose);
      window.removeEventListener("scroll", onRepositionClose, true);
    };
  }, [open]);

  const menu =
    open && typeof document !== "undefined" ? (
      <div
        ref={menuRef}
        id={menuId}
        role="menu"
        style={
          coords
            ? {
                position: "fixed",
                top: coords.top,
                left: coords.left,
                minWidth: coords.minWidth,
              }
            : {
                position: "fixed",
                top: -9999,
                left: -9999,
                visibility: "hidden",
              }
        }
        className="z-[80] overflow-hidden rounded-[var(--radius-md)] border border-border bg-popover py-1 text-popover-foreground shadow-[var(--shadow)]"
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
    ) : null;

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
      {menu ? createPortal(menu, document.body) : null}
    </div>
  );
}
