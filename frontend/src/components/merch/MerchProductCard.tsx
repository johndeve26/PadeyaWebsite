"use client";

import { MerchAccessBadge } from "@/components/merch/MerchAccessBadge";
import { MerchFallbackVisual } from "@/components/merch/MerchFallbackVisual";
import { SponsorBrandedMark } from "@/components/merch/SponsorBrandedMark";
import { Badge, Button } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import { productImageUrl } from "@/lib/merch-fallback";
import {
  productStockStatus,
  productStockTotal,
  stockStatusLabel,
} from "@/lib/merch-stock";
import type { MerchCatalogProduct } from "@/lib/types/merch";

type Props = {
  product: MerchCatalogProduct;
  eventTitle?: string | null;
  compact?: boolean;
  onViewDetails: () => void;
  onPrimaryAction: () => void;
};

function isLocked(product: MerchCatalogProduct) {
  return Boolean(
    product.access_locked || product.teaser_only || !product.access_eligible,
  );
}

function isVaultLock(product: MerchCatalogProduct) {
  return Boolean(product.is_vault_exclusive || product.requires_vault_access);
}

function isTicketLock(product: MerchCatalogProduct) {
  return Boolean(
    product.requires_ticket ||
      product.required_access_type === "ticket" ||
      product.required_access_type === "vip" ||
      product.required_access_type === "check_in",
  );
}

export function primaryMerchCtaLabel(product: MerchCatalogProduct): string {
  const locked = isLocked(product);
  if (locked) {
    if (isVaultLock(product)) return "How to unlock";
    if (isTicketLock(product) || product.requires_ticket) return "Get eligible";
    return "Unlock access";
  }
  const status = productStockStatus(product);
  if (status === "sold_out") return "Sold out";
  if (product.variants.length > 1) return "Choose options";
  return "Add to cart";
}

export function MerchProductCard({
  product,
  eventTitle,
  compact = false,
  onViewDetails,
  onPrimaryAction,
}: Props) {
  const locked = isLocked(product);
  const image = productImageUrl(product);
  const stock = productStockTotal(product);
  const status = productStockStatus(product);
  const fromPrice = Math.min(
    ...[
      ...product.variants.map((v) => Number(v.effective_price)),
      Number(product.base_price),
    ].filter((n) => Number.isFinite(n)),
  );
  const soldOut = !locked && status === "sold_out";
  const blurb = product.short_description || product.description;
  const cta = primaryMerchCtaLabel(product);
  const ships = Boolean(product.shipping_enabled);
  const pickup = product.pickup_enabled !== false;

  const lockCopy = locked
    ? isVaultLock(product)
      ? "Unlock through the host’s Vault to purchase this merch."
      : isTicketLock(product) || product.requires_ticket
        ? "Available to ticket holders for this event."
        : product.unlock_hint ||
          "Unlock access to view variants and purchase."
    : null;

  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card transition-shadow hover:shadow-[var(--shadow)]">
      <button
        type="button"
        onClick={onViewDetails}
        className="relative block aspect-[4/3] w-full overflow-hidden text-left"
        aria-label={`View ${product.name}`}
      >
        {image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={image}
            alt=""
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
          />
        ) : (
          <MerchFallbackVisual
            productType={product.product_type}
            productName={product.name}
            eventTitle={eventTitle || product.event_title}
            compact={compact}
          />
        )}
        {locked ? (
          <span className="absolute bottom-2 left-2 flex flex-wrap gap-1">
            <Badge tone="dark" size="sm">
              Locked
            </Badge>
          </span>
        ) : null}
      </button>

      <div
        className={
          compact
            ? "flex flex-1 flex-col gap-2.5 p-3.5"
            : "flex flex-1 flex-col gap-3 p-4"
        }
      >
        <div className="space-y-1">
          <h3
            className={
              compact
                ? "text-sm font-extrabold tracking-tight text-foreground"
                : "text-base font-extrabold tracking-tight text-foreground"
            }
          >
            {product.name}
          </h3>
          {blurb && !compact ? (
            <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground">
              {blurb}
            </p>
          ) : null}
        </div>

        <p className="text-base font-extrabold text-foreground">
          {formatNgn(fromPrice)}
          {!locked && product.variants.length > 1 ? (
            <span className="ml-1 text-xs font-bold text-muted-foreground">
              from
            </span>
          ) : null}
        </p>

        <div className="flex flex-wrap gap-1.5">
          {locked ? null : (
            <Badge
              tone={
                status === "sold_out"
                  ? "danger"
                  : status === "low_stock"
                    ? "warning"
                    : "success"
              }
              size="sm"
            >
              {stockStatusLabel(status)}
            </Badge>
          )}
          {!locked && pickup ? (
            <Badge tone="outline" size="sm">
              Pickup at event
            </Badge>
          ) : null}
          {!locked && ships ? (
            <Badge tone="outline" size="sm">
              Ships
            </Badge>
          ) : null}
          <MerchAccessBadge product={product} />
        </div>

        {product.is_sponsor_branded && !locked ? (
          <SponsorBrandedMark
            brandName={product.sponsor_brand_name}
            logoUrl={product.sponsor_logo_url}
            compact
          />
        ) : null}

        {locked ? (
          <p className="text-xs leading-relaxed text-muted-foreground">
            {lockCopy}
          </p>
        ) : (
          <p className="text-xs text-muted-foreground">
            {product.variants.length === 1
              ? "1 variant"
              : `${product.variants.length} variants`}
            {!soldOut ? ` · ${stock} left` : ""}
          </p>
        )}

        <div className="mt-auto flex flex-col gap-2 pt-1">
          <Button
            size="sm"
            className="w-full"
            disabled={soldOut}
            variant={soldOut ? "ghost" : undefined}
            onClick={onPrimaryAction}
          >
            {cta}
          </Button>
          <button
            type="button"
            onClick={onViewDetails}
            className="text-center text-xs font-bold text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
          >
            View details
          </button>
        </div>
      </div>
    </article>
  );
}

/** @deprecated Prefer MerchProductCard — kept for smoke / import stability. */
export { MerchProductCard as EventMerchCard };
