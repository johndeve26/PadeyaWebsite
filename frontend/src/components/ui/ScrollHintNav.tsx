"use client";

import {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
  type ComponentPropsWithoutRef,
  type ReactNode,
} from "react";

import { cn } from "@/lib/cn";

const SCROLL_THRESHOLD = 4;

type ScrollHintNavProps = {
  children: ReactNode;
  className?: string;
  scrollClassName?: string;
  /** CSS color for edge fades — should match the nav surface background. */
  fadeFrom?: string;
  showChevrons?: boolean;
} & Pick<ComponentPropsWithoutRef<"nav">, "aria-label">;

function ChevronIcon({ direction }: { direction: "left" | "right" }) {
  return (
    <svg aria-hidden viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none">
      <path
        d={direction === "left" ? "M10 3.5 5.5 8 10 12.5" : "M6 3.5 10.5 8 6 12.5"}
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ScrollHintNav({
  children,
  className,
  scrollClassName,
  fadeFrom = "var(--surface)",
  showChevrons = true,
  "aria-label": ariaLabel,
}: ScrollHintNavProps) {
  const scrollRef = useRef<HTMLElement | null>(null);
  const [hints, setHints] = useState({ left: false, right: false });

  const updateHints = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const { scrollLeft, clientWidth, scrollWidth } = el;
    setHints({
      left: scrollLeft > SCROLL_THRESHOLD,
      right: scrollLeft + clientWidth < scrollWidth - SCROLL_THRESHOLD,
    });
  }, []);

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    updateHints();

    el.addEventListener("scroll", updateHints, { passive: true });
    window.addEventListener("resize", updateHints);

    const ro = new ResizeObserver(updateHints);
    ro.observe(el);
    for (const child of el.children) {
      ro.observe(child);
    }

    return () => {
      el.removeEventListener("scroll", updateHints);
      window.removeEventListener("resize", updateHints);
      ro.disconnect();
    };
  }, [updateHints, children]);

  function scrollBy(direction: "left" | "right") {
    const el = scrollRef.current;
    if (!el) return;
    const delta = Math.max(el.clientWidth * 0.6, 120);
    el.scrollBy({
      left: direction === "left" ? -delta : delta,
      behavior: "smooth",
    });
  }

  const chevronClassName = cn(
    "absolute top-1/2 z-[2] flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-full",
    "border border-border/60 bg-surface/95 text-muted-foreground shadow-sm",
    "transition-colors hover:bg-surface-elevated hover:text-foreground",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
  );

  return (
    <div className={cn("relative min-w-0 w-full max-w-full", className)}>
      {hints.left ? (
        <>
          <div
            aria-hidden
            className="pointer-events-none absolute inset-y-0 left-0 z-[1] w-10"
            style={{
              background: `linear-gradient(to right, ${fadeFrom}, transparent)`,
            }}
          />
          {showChevrons ? (
            <button
              type="button"
              aria-label="Scroll navigation left"
              className={cn(chevronClassName, "left-0.5")}
              onClick={() => scrollBy("left")}
            >
              <ChevronIcon direction="left" />
            </button>
          ) : null}
        </>
      ) : null}

      <nav
        ref={(node) => {
          scrollRef.current = node;
        }}
        aria-label={ariaLabel}
        className={cn(
          "overflow-x-auto overscroll-x-contain [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden",
          scrollClassName,
        )}
      >
        {children}
      </nav>

      {hints.right ? (
        <>
          <div
            aria-hidden
            className="pointer-events-none absolute inset-y-0 right-0 z-[1] w-10"
            style={{
              background: `linear-gradient(to left, ${fadeFrom}, transparent)`,
            }}
          />
          {showChevrons ? (
            <button
              type="button"
              aria-label="Scroll navigation right"
              className={cn(chevronClassName, "right-0.5")}
              onClick={() => scrollBy("right")}
            >
              <ChevronIcon direction="right" />
            </button>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
