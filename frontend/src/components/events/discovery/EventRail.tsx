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

import { EventCarouselControls } from "@/components/events/discovery/EventCarouselControls";
import { cn } from "@/lib/cn";

type EventRailProps = {
  children: ReactNode;
  label: string;
  title?: string;
  description?: string;
  action?: ReactNode;
  /** Slide width while scrolling. */
  slideClassName?: string;
  className?: string;
  tone?: "dark" | "light";
  /** Show prev/next on desktop (always on mobile when >1). Default true. */
  showControls?: boolean;
};

/**
 * Horizontal snap rail — stays scrollable on desktop (4–5 cards visible)
 * with prev/next controls. Mobile uses touch snap scroll.
 */
export function EventRail({
  children,
  label,
  title,
  description,
  action,
  slideClassName = "w-[min(78vw,17.5rem)] sm:w-[15.5rem] lg:w-[16.25rem]",
  className = "",
  tone = "dark",
  showControls = true,
}: EventRailProps) {
  const items = Children.toArray(children).filter(Boolean);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const [canPrev, setCanPrev] = useState(false);
  const [canNext, setCanNext] = useState(false);
  const labelId = useId();
  const dark = tone === "dark";

  const sync = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const max = el.scrollWidth - el.clientWidth;
    setCanPrev(el.scrollLeft > 4);
    setCanNext(max > 4 && el.scrollLeft < max - 4);
  }, []);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    sync();
    el.addEventListener("scroll", sync, { passive: true });
    window.addEventListener("resize", sync);
    return () => {
      el.removeEventListener("scroll", sync);
      window.removeEventListener("resize", sync);
    };
  }, [sync, items.length]);

  function scrollByDir(dir: -1 | 1) {
    const el = scrollerRef.current;
    if (!el) return;
    const first = el.querySelector<HTMLElement>("[data-rail-item]");
    const step = (first?.offsetWidth ?? el.clientWidth * 0.7) + 16;
    el.scrollBy({ left: dir * step, behavior: "smooth" });
  }

  if (!items.length) return null;

  return (
    <section className={cn("min-w-0 space-y-4 overflow-x-clip", className)}>
      {(title || action || (showControls && items.length > 1)) && (
        <div className="flex min-w-0 items-end justify-between gap-3">
          <div className="min-w-0 space-y-1">
            {title ? (
              <h2
                id={labelId}
                className={cn(
                  "text-balance text-xl font-extrabold tracking-tight sm:text-2xl",
                  dark ? "text-paper" : "text-foreground",
                )}
              >
                {title}
              </h2>
            ) : (
              <p id={labelId} className="sr-only">
                {label}
              </p>
            )}
            {description ? (
              <p
                className={cn(
                  "max-w-xl text-sm",
                  dark ? "text-paper/65" : "text-muted-foreground",
                )}
              >
                {description}
              </p>
            ) : null}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {action}
            {showControls && items.length > 1 ? (
              <EventCarouselControls
                label={label}
                onPrev={() => scrollByDir(-1)}
                onNext={() => scrollByDir(1)}
                canPrev={canPrev}
                canNext={canNext}
                tone={tone}
                className="hidden sm:flex"
              />
            ) : null}
          </div>
        </div>
      )}

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
          "flex gap-4 overflow-x-auto scroll-smooth pb-1",
          "[-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden",
          "snap-x snap-mandatory",
        )}
      >
        {items.map((child, i) => (
          <div
            key={i}
            data-rail-item
            className={cn("shrink-0 snap-start", slideClassName)}
          >
            {child}
          </div>
        ))}
      </div>

      {showControls && items.length > 1 ? (
        <EventCarouselControls
          label={label}
          onPrev={() => scrollByDir(-1)}
          onNext={() => scrollByDir(1)}
          canPrev={canPrev}
          canNext={canNext}
          tone={tone}
          className="sm:hidden"
        />
      ) : null}
    </section>
  );
}
