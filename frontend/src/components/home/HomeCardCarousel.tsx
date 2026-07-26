"use client";

import {
  Children,
  type ReactNode,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";

import { cn } from "@/lib/cn";

type HomeCardCarouselProps = {
  children: ReactNode;
  /** Accessible name for the slide region. */
  label: string;
  /**
   * Grid column classes applied once the carousel collapses to a grid.
   * Include breakpoint prefixes that match `until` (e.g. `sm:grid-cols-2 lg:grid-cols-3`
   * when `until="sm"`).
   */
  desktopGridClassName?: string;
  /** Width of each slide while in carousel mode. */
  slideClassName?: string;
  className?: string;
  /**
   * Carousel below this breakpoint; CSS grid from this breakpoint up.
   * - `sm` = mobile only (default for picks/trending)
   * - `lg` = mobile + tablet
   */
  until?: "sm" | "lg";
  /** Control chrome for light or dark section backgrounds. */
  tone?: "light" | "dark";
};

/**
 * Horizontal snap carousel with prev/next + dots below `until`,
 * then a normal CSS grid at/above that breakpoint.
 */
export function HomeCardCarousel({
  children,
  label,
  desktopGridClassName = "sm:grid-cols-2 lg:grid-cols-3",
  slideClassName = "w-[min(82vw,19.5rem)]",
  className = "",
  until = "sm",
  tone = "light",
}: HomeCardCarouselProps) {
  const items = Children.toArray(children).filter(Boolean);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);
  const labelId = useId();
  const dark = tone === "dark";

  const gridAt =
    until === "sm"
      ? {
          controlsHide: "sm:hidden",
          track: "sm:grid sm:gap-5 sm:overflow-visible sm:pb-0 sm:snap-none",
          item: "sm:w-auto sm:min-w-0 sm:snap-align-none",
        }
      : {
          controlsHide: "lg:hidden",
          track: "lg:grid lg:gap-5 lg:overflow-visible lg:pb-0 lg:snap-none",
          item: "lg:w-auto lg:min-w-0 lg:snap-align-none",
        };

  const syncActive = useCallback(() => {
    const el = scrollerRef.current;
    if (!el || !items.length) return;
    const first = el.querySelector<HTMLElement>("[data-carousel-item]");
    if (!first) return;
    const gap = 16;
    const step = first.offsetWidth + gap;
    if (step <= 0) return;
    const idx = Math.round(el.scrollLeft / step);
    setActive(Math.max(0, Math.min(items.length - 1, idx)));
  }, [items.length]);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    syncActive();
    el.addEventListener("scroll", syncActive, { passive: true });
    window.addEventListener("resize", syncActive);
    return () => {
      el.removeEventListener("scroll", syncActive);
      window.removeEventListener("resize", syncActive);
    };
  }, [syncActive]);

  function scrollByDir(dir: -1 | 1) {
    const el = scrollerRef.current;
    if (!el) return;
    const first = el.querySelector<HTMLElement>("[data-carousel-item]");
    const step = (first?.offsetWidth ?? el.clientWidth * 0.8) + 16;
    el.scrollBy({ left: dir * step, behavior: "smooth" });
  }

  function goTo(i: number) {
    const el = scrollerRef.current;
    if (!el) return;
    const target = el.querySelectorAll<HTMLElement>("[data-carousel-item]")[i];
    target?.scrollIntoView({
      behavior: "smooth",
      inline: "start",
      block: "nearest",
    });
  }

  if (!items.length) return null;

  return (
    <div className={cn("min-w-0 space-y-3", className)}>
      <div
        className={cn(
          "flex items-center justify-between gap-3",
          gridAt.controlsHide,
        )}
      >
        <p id={labelId} className="sr-only">
          {label}
        </p>
        <div className="flex gap-2">
          <CarouselButton
            label="Previous"
            onClick={() => scrollByDir(-1)}
            disabled={active <= 0}
            dark={dark}
          >
            ←
          </CarouselButton>
          <CarouselButton
            label="Next"
            onClick={() => scrollByDir(1)}
            disabled={active >= items.length - 1}
            dark={dark}
          >
            →
          </CarouselButton>
        </div>
        <div
          className="flex items-center gap-1.5"
          role="tablist"
          aria-label={`${label} slides`}
        >
          {items.map((_, i) => (
            <button
              key={i}
              type="button"
              role="tab"
              aria-selected={i === active}
              aria-label={`Slide ${i + 1} of ${items.length}`}
              onClick={() => goTo(i)}
              className="inline-flex h-11 w-11 items-center justify-center rounded-full"
            >
              <span
                aria-hidden
                className={cn(
                  "rounded-full transition-all",
                  i === active
                    ? "h-1.5 w-5 bg-primary"
                    : dark
                      ? "h-1.5 w-1.5 bg-paper/35 hover:bg-paper/55"
                      : "h-1.5 w-1.5 bg-border hover:bg-muted-foreground/40",
                )}
              />
            </button>
          ))}
        </div>
      </div>

      <div
        ref={scrollerRef}
        role="region"
        aria-labelledby={labelId}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "ArrowLeft") {
            e.preventDefault();
            scrollByDir(-1);
          }
          if (e.key === "ArrowRight") {
            e.preventDefault();
            scrollByDir(1);
          }
        }}
        className={cn(
          "flex gap-4 overflow-x-auto scroll-smooth pb-1 [-ms-overflow-style:none] [scrollbar-width:none] snap-x snap-mandatory",
          "[&::-webkit-scrollbar]:hidden",
          gridAt.track,
          desktopGridClassName,
        )}
      >
        {items.map((child, i) => (
          <div
            key={i}
            data-carousel-item
            className={cn("shrink-0 snap-start", slideClassName, gridAt.item)}
          >
            {child}
          </div>
        ))}
      </div>
    </div>
  );
}

function CarouselButton({
  label,
  onClick,
  disabled,
  children,
  dark = false,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  children: ReactNode;
  dark?: boolean;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex h-11 w-11 items-center justify-center rounded-full border text-base font-bold shadow-[var(--shadow-soft)] transition",
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
