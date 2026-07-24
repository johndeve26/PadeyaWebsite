"use client";

import { usePathname } from "next/navigation";
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import { isResourcesNavActive } from "@/components/layout/headerNav";
import { ResourcesMegaPanel } from "@/components/layout/ResourcesMegaPanel";
import { cn } from "@/lib/cn";

const navLinkBase =
  "rounded-[var(--radius-sm)] px-2.5 py-2 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 xl:px-3";

const CLOSE_DELAY_MS = 180;
const VIEWPORT_GUTTER_PX = 12;
const PANEL_GAP_PX = 10;

export function HeaderResourcesDropdown({
  tone = "default",
}: {
  tone?: "default" | "onDark";
}) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const menuId = useId();
  const active = isResourcesNavActive(pathname);
  const onDark = tone === "onDark";

  const clearCloseTimer = useCallback(() => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  }, []);

  const openMenu = useCallback(() => {
    clearCloseTimer();
    setOpen(true);
  }, [clearCloseTimer]);

  const scheduleClose = useCallback(() => {
    clearCloseTimer();
    closeTimer.current = setTimeout(() => setOpen(false), CLOSE_DELAY_MS);
  }, [clearCloseTimer]);

  const closeMenu = useCallback(() => {
    clearCloseTimer();
    setOpen(false);
  }, [clearCloseTimer]);

  useEffect(() => () => clearCloseTimer(), [clearCloseTimer]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) closeMenu();
    };
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        closeMenu();
        root.current?.querySelector<HTMLElement>("[data-resources-trigger]")?.focus();
      }
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, closeMenu]);

  const repositionPanel = useCallback(() => {
    const rootEl = root.current;
    const trigger = triggerRef.current;
    const panel = rootEl?.querySelector<HTMLElement>("[role='menu']");
    if (!rootEl || !trigger || !panel) return;

    panel.style.right = "auto";
    panel.style.transform = "";

    const triggerRect = trigger.getBoundingClientRect();
    const rootRect = rootEl.getBoundingClientRect();
    const panelWidth = panel.offsetWidth;
    const triggerCenterX = triggerRect.left + triggerRect.width / 2;

    let panelLeftViewport = triggerCenterX - panelWidth / 2;
    const maxLeft = window.innerWidth - panelWidth - VIEWPORT_GUTTER_PX;
    panelLeftViewport = Math.max(
      VIEWPORT_GUTTER_PX,
      Math.min(panelLeftViewport, maxLeft),
    );

    panel.style.left = `${panelLeftViewport - rootRect.left}px`;
    panel.style.top = `${triggerRect.bottom - rootRect.top + PANEL_GAP_PX}px`;
    panel.style.setProperty("--resources-panel-gap", `${PANEL_GAP_PX}px`);
  }, []);

  useEffect(() => {
    if (!open) return;

    repositionPanel();
    const frame = requestAnimationFrame(repositionPanel);

    window.addEventListener("resize", repositionPanel);
    window.addEventListener("scroll", repositionPanel, true);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", repositionPanel);
      window.removeEventListener("scroll", repositionPanel, true);
    };
  }, [open, pathname, repositionPanel]);

  const onTriggerKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openMenu();
      requestAnimationFrame(() => {
        const first = root.current?.querySelector<HTMLElement>(
          "[role='menu'] a[href], [role='menu'] [role='menuitem']",
        );
        first?.focus();
      });
    } else if (e.key === "Escape") {
      closeMenu();
    }
  };

  const onPanelKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const panel = root.current?.querySelector<HTMLElement>("[role='menu']");
    if (!panel) return;
    const items = [
      ...panel.querySelectorAll<HTMLElement>("a[href], [role='menuitem']"),
    ];
    if (items.length === 0) return;
    const idx = items.indexOf(document.activeElement as HTMLElement);

    if (e.key === "ArrowDown") {
      e.preventDefault();
      const next = items[(idx + 1 + items.length) % items.length]!;
      next.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prev = items[(idx - 1 + items.length) % items.length]!;
      prev.focus();
    } else if (e.key === "Home") {
      e.preventDefault();
      items[0]!.focus();
    } else if (e.key === "End") {
      e.preventDefault();
      items[items.length - 1]!.focus();
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeMenu();
      root.current?.querySelector<HTMLElement>("[data-resources-trigger]")?.focus();
    }
  };

  return (
    <div
      ref={root}
      className="relative inline-flex"
      onMouseEnter={openMenu}
      onMouseLeave={scheduleClose}
    >
      <button
        ref={triggerRef}
        type="button"
        data-resources-trigger
        className={cn(
          navLinkBase,
          "inline-flex items-center gap-1.5",
          onDark
            ? cn(
                "focus-visible:ring-offset-ink",
                active
                  ? "bg-paper text-ink"
                  : "text-paper/80 hover:bg-paper/10 hover:text-paper",
              )
            : cn(
                "focus-visible:ring-offset-background",
                active
                  ? "bg-ink text-paper"
                  : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
              ),
        )}
        aria-label="Resources menu"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-controls={open ? menuId : undefined}
        onClick={() => (open ? closeMenu() : openMenu())}
        onKeyDown={onTriggerKeyDown}
      >
        Resources
        <span className="text-[0.65rem] opacity-70" aria-hidden>
          ▾
        </span>
      </button>
      {open ? (
        <div onKeyDown={onPanelKeyDown}>
          <ResourcesMegaPanel
            id={menuId}
            pathname={pathname}
            onNavigate={closeMenu}
          />
        </div>
      ) : null}
    </div>
  );
}
