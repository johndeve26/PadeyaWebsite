"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";

import { SkeletonCard } from "@/components/ui";
import { cn } from "@/lib/cn";

type Props = {
  children: ReactNode;
  className?: string;
  skeletonHeight?: string;
  /** Render immediately (above the fold). */
  eager?: boolean;
};

export function LazyMarketplaceSection({
  children,
  className,
  skeletonHeight = "min-h-[12rem]",
  eager = false,
}: Props) {
  const ref = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(eager);

  useEffect(() => {
    if (eager || visible) return;
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setVisible(true);
          io.disconnect();
        }
      },
      { rootMargin: "200px 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [eager, visible]);

  return (
    <section ref={ref} className={cn(className)}>
      {visible ? (
        children
      ) : (
        <div
          className={cn("grid gap-4 sm:grid-cols-2 lg:grid-cols-3", skeletonHeight)}
          aria-hidden
        >
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}
    </section>
  );
}
