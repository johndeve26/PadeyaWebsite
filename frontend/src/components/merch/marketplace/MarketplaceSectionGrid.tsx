"use client";

import { type ReactNode } from "react";

import { HomeCardCarousel } from "@/components/home/HomeCardCarousel";
import { MarketplaceDropCard } from "@/components/merch/marketplace/MarketplaceDropCard";
import { MarketplaceProductCard } from "@/components/merch/marketplace/MarketplaceProductCard";
import { MarketplaceVaultCard } from "@/components/merch/marketplace/MarketplaceVaultCard";
import { SkeletonCard } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  MARKETPLACE_CAROUSEL_GRID,
  MARKETPLACE_CAROUSEL_SLIDE,
  MARKETPLACE_PRODUCT_GRID,
} from "@/lib/merch/marketplace-layout";
import type { MarketplaceProduct } from "@/lib/types/merch";

export type MarketplaceSectionVariant = "product" | "drops" | "vault";

type Props = {
  products: MarketplaceProduct[];
  loading?: boolean;
  empty?: ReactNode;
  className?: string;
  skeletonCount?: number;
  variant?: MarketplaceSectionVariant;
  limit?: number;
  /** Accessible name for the mobile carousel region. */
  label?: string;
};

function renderCard(product: MarketplaceProduct, variant: MarketplaceSectionVariant) {
  if (variant === "drops") return <MarketplaceDropCard product={product} />;
  if (variant === "vault") return <MarketplaceVaultCard product={product} />;
  return <MarketplaceProductCard product={product} />;
}

/** Curated marketplace sections — snap carousel on mobile, 4-col grid from sm. */
export function MarketplaceSectionGrid({
  products,
  loading = false,
  empty,
  className,
  skeletonCount = 4,
  variant = "product",
  limit,
  label = "Merch products",
}: Props) {
  const visible = limit ? products.slice(0, limit) : products;

  if (loading) {
    return (
      <div className={cn(MARKETPLACE_PRODUCT_GRID, className)}>
        {Array.from({ length: skeletonCount }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (visible.length === 0) {
    return empty ? <>{empty}</> : null;
  }

  return (
    <HomeCardCarousel
      label={label}
      until="sm"
      desktopGridClassName={MARKETPLACE_CAROUSEL_GRID}
      slideClassName={MARKETPLACE_CAROUSEL_SLIDE}
      className={className}
    >
      {visible.map((product) => (
        <div
          key={`${product.id}-${product.host_slug ?? ""}`}
          className="min-w-0 h-full"
        >
          {renderCard(product, variant)}
        </div>
      ))}
    </HomeCardCarousel>
  );
}
