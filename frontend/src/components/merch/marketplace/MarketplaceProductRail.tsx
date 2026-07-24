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

import { MarketplaceDropCard } from "@/components/merch/marketplace/MarketplaceDropCard";
import { MarketplaceProductCard } from "@/components/merch/marketplace/MarketplaceProductCard";
import { MarketplaceVaultCard } from "@/components/merch/marketplace/MarketplaceVaultCard";
import { EventCarouselControls } from "@/components/events/discovery/EventCarouselControls";
import { SkeletonCard } from "@/components/ui";
import { cn } from "@/lib/cn";
import { MARKETPLACE_RAIL_ITEM } from "@/lib/merch/marketplace-layout";
import type { MarketplaceProduct } from "@/lib/types/merch";

type RailVariant = "default" | "featured" | "drops" | "vault" | "event";

type Props = {
  products: MarketplaceProduct[];
  loading?: boolean;
  empty?: ReactNode;
  className?: string;
  skeletonCount?: number;
  variant?: RailVariant;
  label?: string;
  /** Max items to render (curated sections). */
  limit?: number;
  /** Desktop grid cols when not using horizontal rail. */
  gridOnDesktop?: boolean;
};

function renderCard(product: MarketplaceProduct, variant: RailVariant) {
  if (variant === "drops") {
    return <MarketplaceDropCard product={product} />;
  }
  if (variant === "vault") {
    return <MarketplaceVaultCard product={product} />;
  }
  return (
    <MarketplaceProductCard product={product} />
  );
}

export function MarketplaceProductRail({
  products,
  loading = false,
  empty,
  className,
  skeletonCount = 4,
  variant = "default",
  label = "Products",
  limit,
  gridOnDesktop = false,
}: Props) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const [canPrev, setCanPrev] = useState(false);
  const [canNext, setCanNext] = useState(false);
  const labelId = useId();

  const visible = limit ? products.slice(0, limit) : products;
  const items = Children.toArray(
    visible.map((product) => (
      <div
        key={`${product.id}-${product.host_slug ?? ""}`}
        data-rail-item
        className={cn(MARKETPLACE_RAIL_ITEM, gridOnDesktop && "md:min-w-0")}
      >
        {renderCard(product, variant)}
      </div>
    )),
  );

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
  }, [sync, visible.length]);

  function scrollByDir(dir: -1 | 1) {
    const el = scrollerRef.current;
    if (!el) return;
    const first = el.querySelector<HTMLElement>("[data-rail-item]");
    const step = (first?.offsetWidth ?? el.clientWidth * 0.75) + 16;
    el.scrollBy({ left: dir * step, behavior: "smooth" });
  }

  if (loading) {
    const gridClass = gridOnDesktop
      ? "md:grid md:grid-cols-2 md:overflow-visible lg:grid-cols-3 xl:grid-cols-4"
      : "";
    return (
      <div
        className={cn(
          "flex gap-4 overflow-x-auto pb-2",
          gridClass,
          className,
        )}
      >
        {Array.from({ length: skeletonCount }).map((_, i) => (
          <SkeletonCard
            key={i}
            className={cn("min-w-[17rem]", gridOnDesktop && "md:min-w-0")}
          />
        ))}
      </div>
    );
  }

  if (visible.length === 0) {
    return empty ? <>{empty}</> : null;
  }

  const useRail = !gridOnDesktop || visible.length > 4;

  if (!useRail && gridOnDesktop) {
    return (
      <div
        className={cn(
          "grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
          className,
        )}
      >
        {items}
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center justify-end">
        <EventCarouselControls
          label={label}
          canPrev={canPrev}
          canNext={canNext}
          onPrev={() => scrollByDir(-1)}
          onNext={() => scrollByDir(1)}
          tone="light"
        />
      </div>
      <div
        ref={scrollerRef}
        role="region"
        aria-labelledby={labelId}
        className={cn(
          "flex gap-4 overflow-x-auto pb-2 snap-x snap-mandatory scrollbar-none",
          "md:snap-none",
        )}
      >
        <span id={labelId} className="sr-only">
          {label}
        </span>
        {items}
      </div>
    </div>
  );
}
