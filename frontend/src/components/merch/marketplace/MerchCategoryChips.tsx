"use client";

import Link from "next/link";

import { cn } from "@/lib/cn";
import { MERCH_CATEGORIES } from "@/lib/merch-product-types";
import type { MarketplaceCategory } from "@/lib/types/merch";

/** Preferred marketplace browse order (subset of MERCH_CATEGORIES). */
const DISPLAY_SLUGS = [
  "apparel",
  "caps",
  "wristbands",
  "posters",
  "bundles",
  "digital",
  "collectibles",
  "accessories",
  "food_drink",
] as const;

const DISPLAY_LABELS: Record<string, string> = {
  apparel: "Apparel",
  caps: "Caps",
  wristbands: "Wristbands",
  posters: "Posters",
  bundles: "Bundles",
  digital: "Digital",
  collectibles: "Collectibles",
  accessories: "Accessories",
  food_drink: "Vouchers",
};

type Props = {
  categories?: MarketplaceCategory[];
  activeCategory?: string;
  onSelect?: (slug: string) => void;
  className?: string;
};

export function MerchCategoryChips({
  categories,
  activeCategory,
  onSelect,
  className,
}: Props) {
  const fromApi = categories?.length
    ? categories.map((c) => ({ slug: c.slug, name: c.name }))
    : null;

  const items = fromApi
    ? DISPLAY_SLUGS.map((slug) => {
        const match = fromApi.find((c) => c.slug === slug);
        return {
          slug,
          name: match?.name ?? DISPLAY_LABELS[slug] ?? slug,
        };
      })
    : DISPLAY_SLUGS.map((slug) => {
        const known = MERCH_CATEGORIES.find((c) => c.value === slug);
        return {
          slug,
          name:
            DISPLAY_LABELS[slug] ??
            known?.label ??
            slug.replace(/_/g, " "),
        };
      });

  return (
    <div
      className={cn(
        "flex flex-wrap gap-2 sm:gap-2.5",
        className,
      )}
      role="list"
      aria-label="Merch categories"
    >
      {items.map((cat) => {
        const selected = activeCategory === cat.slug;
        const href = `/merch?category=${encodeURIComponent(cat.slug)}#catalog`;
        const chipClass = cn(
          "rounded-full border px-3.5 py-2 text-sm font-bold transition-colors",
          selected
            ? "border-primary bg-primary/10 text-primary-text"
            : "border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground dark:bg-surface-elevated",
        );

        if (onSelect) {
          return (
            <button
              key={cat.slug}
              type="button"
              role="listitem"
              onClick={() => onSelect(cat.slug)}
              className={chipClass}
            >
              {cat.name}
            </button>
          );
        }

        return (
          <Link
            key={cat.slug}
            href={href}
            role="listitem"
            className={chipClass}
          >
            {cat.name}
          </Link>
        );
      })}
    </div>
  );
}
