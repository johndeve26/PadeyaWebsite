"use client";

import Link from "next/link";

import { MerchFallbackVisual } from "@/components/merch/MerchFallbackVisual";
import { Badge, Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatDate, formatNgn } from "@/lib/format";
import { dropEligibilityLabel } from "@/lib/merch/marketplace-curation";
import {
  MARKETPLACE_CARD_BODY,
  MARKETPLACE_CARD_IMAGE,
  MARKETPLACE_CARD_PRICE,
  MARKETPLACE_CARD_TITLE,
} from "@/lib/merch/marketplace-layout";
import { productImageUrl } from "@/lib/merch-fallback";
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

function dropCountdownLabel(
  endsAt?: string | null,
  live?: boolean,
): string | null {
  if (live) return "Live now";
  if (!endsAt) return null;
  const end = new Date(endsAt).getTime();
  if (Number.isNaN(end)) return null;
  const diff = end - Date.now();
  if (diff <= 0) return "Ended";
  const days = Math.floor(diff / 86_400_000);
  const hours = Math.floor((diff % 86_400_000) / 3_600_000);
  if (days > 0) return `${days}d ${hours}h left`;
  const mins = Math.floor((diff % 3_600_000) / 60_000);
  if (hours > 0) return `${hours}h ${mins}m left`;
  return `${mins}m left`;
}

export function MarketplaceDropCard({ product, className }: Props) {
  const image = productImageUrl(product);
  const href = productHref(product);
  const eligibility =
    dropEligibilityLabel(product.audience) ||
    product.access_label ||
    null;
  const live = product.is_drop_live;
  const endsAt = product.sales_end_at ?? product.post_event_drop_at ?? null;
  const statusLabel = live
    ? "Live now"
    : dropCountdownLabel(endsAt, live);

  return (
    <article
      className={cn(
        "group relative flex h-full flex-col overflow-hidden rounded-[var(--radius-lg)] border border-primary/30 bg-gradient-to-b from-primary/10 to-ink text-paper sm:min-w-0",
        className,
      )}
    >
      <Link href={href} className={MARKETPLACE_CARD_IMAGE}>
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
          <Badge tone="accent" size="sm">
            {live ? "Live now" : "Limited drop"}
          </Badge>
          {eligibility ? (
            <Badge tone="warning" size="sm">
              {eligibility}
            </Badge>
          ) : null}
          {statusLabel && !live ? (
            <Badge tone="dark" size="sm">
              {statusLabel}
            </Badge>
          ) : null}
        </div>
      </Link>
      <div className={MARKETPLACE_CARD_BODY}>
        <h3 className={MARKETPLACE_CARD_TITLE}>
          <Link href={href} className="hover:text-primary">
            {product.name}
          </Link>
        </h3>
        {product.event_title ? (
          <p className="line-clamp-1 text-xs font-semibold text-paper/55">
            {product.event_title}
            {product.event_start_at
              ? ` · ${formatDate(product.event_start_at)}`
              : null}
          </p>
        ) : null}
        {product.host_name ? (
          <p className="truncate text-sm text-paper/60">{product.host_name}</p>
        ) : null}
        <div className="mt-auto flex items-end justify-between gap-2 pt-1">
          <p className={MARKETPLACE_CARD_PRICE}>
            {formatNgn(Number(product.base_price))}
          </p>
          <Link href={href}>
            <Button size="sm" variant="outline-dark">
              View drop
            </Button>
          </Link>
        </div>
      </div>
    </article>
  );
}
