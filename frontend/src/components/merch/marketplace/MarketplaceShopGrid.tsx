"use client";

import { type ReactNode } from "react";

import { HomeCardCarousel } from "@/components/home/HomeCardCarousel";
import { MarketplaceProductCard } from "@/components/merch/marketplace/MarketplaceProductCard";
import { Button, SkeletonCard } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  MARKETPLACE_CAROUSEL_GRID,
  MARKETPLACE_CAROUSEL_SLIDE,
  MARKETPLACE_PRODUCT_GRID,
} from "@/lib/merch/marketplace-layout";
import type { MarketplaceProduct } from "@/lib/types/merch";

type Props = {
  products: MarketplaceProduct[];
  loading?: boolean;
  loadingMore?: boolean;
  empty?: ReactNode;
  hasMore?: boolean;
  onLoadMore?: () => void;
  className?: string;
  skeletonCount?: number;
  label?: string;
};

export function MarketplaceShopGrid({
  products,
  loading = false,
  loadingMore = false,
  empty,
  hasMore = false,
  onLoadMore,
  className,
  skeletonCount = 12,
  label = "Shop all merch",
}: Props) {
  if (loading) {
    return (
      <div className={cn(MARKETPLACE_PRODUCT_GRID, className)}>
        {Array.from({ length: skeletonCount }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (products.length === 0) {
    return empty ? <>{empty}</> : null;
  }

  return (
    <div className={cn("space-y-8", className)}>
      <HomeCardCarousel
        label={label}
        until="sm"
        desktopGridClassName={MARKETPLACE_CAROUSEL_GRID}
        slideClassName={MARKETPLACE_CAROUSEL_SLIDE}
      >
        {products.map((product) => (
          <div
            key={`${product.id}-${product.host_slug ?? ""}`}
            className="min-w-0 h-full"
          >
            <MarketplaceProductCard product={product} />
          </div>
        ))}
        {loadingMore
          ? Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={`more-${i}`} />
            ))
          : null}
      </HomeCardCarousel>
      {hasMore && onLoadMore ? (
        <div className="flex justify-center">
          <Button
            type="button"
            variant="secondary"
            size="lg"
            onClick={onLoadMore}
            disabled={loadingMore}
          >
            {loadingMore ? "Loading…" : "Load more"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
