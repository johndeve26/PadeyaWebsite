"use client";

import Link from "next/link";

import { MerchFallbackVisual } from "@/components/merch/MerchFallbackVisual";
import { Badge, Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatDate, formatNgn } from "@/lib/format";
import { productImageUrl } from "@/lib/merch-fallback";
import {
  MARKETPLACE_CARD_BODY,
  MARKETPLACE_CARD_IMAGE,
  MARKETPLACE_CARD_PRICE,
  MARKETPLACE_CARD_TITLE,
} from "@/lib/merch/marketplace-layout";
import type { MarketplaceProduct } from "@/lib/types/merch";

type Props = {
  product: MarketplaceProduct;
  className?: string;
};

function productHref(product: MarketplaceProduct): string {
  if (product.marketplace_path) return product.marketplace_path;
  const host = product.host_slug || product.host_username;
  return host
    ? `/merch/${product.slug}?h=${encodeURIComponent(host)}`
    : `/merch/${product.slug}`;
}

function badgeTone(
  badge: string,
): "accent" | "dark" | "danger" | "warning" | "neutral" {
  const lower = badge.toLowerCase();
  if (lower.includes("sold out")) return "danger";
  if (lower.includes("limited") || lower.includes("vault")) return "warning";
  if (
    lower.includes("standalone") ||
    lower.includes("add-on") ||
    lower.includes("drop") ||
    lower.includes("event")
  ) {
    return "accent";
  }
  if (lower.includes("pickup") || lower.includes("delivery")) return "neutral";
  return "dark";
}

function availabilityText(product: MarketplaceProduct): string | null {
  if (product.availability === "sold_out") return "Sold out";
  if (product.availability === "coming_soon") return "Coming soon";
  const total = product.variants.reduce(
    (sum, v) => sum + (v.available_quantity ?? v.inventory_count ?? 0),
    0,
  );
  if (total > 0 && total <= 5) return "Low stock";
  if (product.pickup_enabled !== false) return "Pickup available";
  if (product.shipping_enabled) return "Delivery available";
  return null;
}

function buildBadges(product: MarketplaceProduct): string[] {
  if (product.badges?.length) return product.badges.slice(0, 4);
  return [
    product.marketplace_kind === "vault_exclusive" || product.is_vault_exclusive
      ? "Vault"
      : null,
    product.marketplace_kind === "post_event_drop" || product.is_post_event_drop
      ? "Drop"
      : null,
    product.marketplace_kind === "bundle" ? "Bundle" : null,
    product.marketplace_kind === "event_addon" ? "Add-on" : null,
    product.marketplace_kind === "event_merch" ? "Event merch" : null,
    product.marketplace_kind === "standalone" || product.is_merch_only
      ? "Standalone"
      : null,
    product.is_featured ? "Featured" : null,
    product.availability === "sold_out" ? "Sold out" : null,
    product.pickup_enabled !== false ? "Pickup" : null,
    product.shipping_enabled ? "Delivery" : null,
  ].filter(Boolean) as string[];
}

export function MarketplaceProductCard({
  product,
  className,
}: Props) {
  const image = productImageUrl(product);
  const href = productHref(product);
  const fromPrice = Math.min(
    ...[
      ...product.variants.map((v) => Number(v.effective_price)),
      Number(product.base_price),
    ].filter((n) => Number.isFinite(n)),
  );
  const badges = buildBadges(product);
  const availability = availabilityText(product);

  return (
    <article
      className={cn(
        "group flex h-full flex-col overflow-hidden rounded-[var(--radius-lg)] border border-border/80 bg-ink text-paper sm:min-w-0",
        className,
      )}
    >
      <Link
        href={href}
        className={MARKETPLACE_CARD_IMAGE}
        aria-label={`View ${product.name}`}
      >
        {image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={image}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
          />
        ) : (
          <MerchFallbackVisual
            productType={product.product_type}
            productName={product.name}
            eventTitle={product.event_title}
            category={product.category}
            compact
          />
        )}
        <div className="absolute inset-x-0 top-0 flex flex-wrap gap-1.5 p-3">
          {badges.slice(0, 3).map((badge) => (
            <Badge key={badge} tone={badgeTone(badge)} size="sm">
              {badge}
            </Badge>
          ))}
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-ink/90 to-transparent" />
      </Link>

      <div className={MARKETPLACE_CARD_BODY}>
        <div className="space-y-0.5">
          <h3 className={MARKETPLACE_CARD_TITLE}>
            <Link href={href} className="hover:text-primary">
              {product.name}
            </Link>
          </h3>
          {product.host_name ? (
            <p className="truncate text-sm font-semibold text-paper/60">
              {product.host_name}
            </p>
          ) : null}
          {product.event_title ? (
            <p className="line-clamp-1 text-xs font-semibold text-paper/50">
              {product.event_title}
              {product.event_start_at
                ? ` · ${formatDate(product.event_start_at)}`
                : null}
            </p>
          ) : null}
          {availability ? (
            <p className="text-xs font-bold text-primary/90">{availability}</p>
          ) : null}
        </div>

        <div className="mt-auto flex items-end justify-between gap-2 pt-1">
          <p className={MARKETPLACE_CARD_PRICE}>
            {Number.isFinite(fromPrice) ? formatNgn(fromPrice) : "—"}
          </p>
          <Link href={href}>
            <Button size="sm" variant="outline-dark">
              View item
            </Button>
          </Link>
        </div>
      </div>
    </article>
  );
}
