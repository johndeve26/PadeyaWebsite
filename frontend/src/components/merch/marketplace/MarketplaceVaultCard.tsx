"use client";

import Link from "next/link";

import { MerchFallbackVisual } from "@/components/merch/MerchFallbackVisual";
import { Badge, Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatNgn } from "@/lib/format";
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

export function MarketplaceVaultCard({ product, className }: Props) {
  const locked =
    Boolean(product.access_locked || product.teaser_only) &&
    !product.access_eligible;
  const image = locked ? null : productImageUrl(product);
  const href = productHref(product);
  const host = product.host_slug || product.host_username;
  const vaultHref = host ? `/@${host}/vault` : "/merch/vault";

  if (locked) {
    return (
      <article
        className={cn(
          "flex h-full flex-col overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card dark:bg-surface-elevated sm:min-w-0",
          className,
        )}
      >
        <div className={cn(MARKETPLACE_CARD_IMAGE, "relative")}>
          <MerchFallbackVisual
            productType={product.product_type}
            productName={product.name}
            category={product.category}
            compact
          />
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-ink/70 p-4 text-center">
            <Badge tone="warning" size="sm">
              Vault exclusive
            </Badge>
            <p className="line-clamp-2 text-base font-extrabold text-paper">
              {product.name || "Vault exclusive merch"}
            </p>
            {product.host_name ? (
              <p className="text-sm font-semibold text-paper/70">
                {product.host_name}
              </p>
            ) : null}
            {product.base_price != null ? (
              <p className="text-sm font-bold text-primary">
                {formatNgn(Number(product.base_price))}
              </p>
            ) : null}
            <p className="text-xs font-semibold text-paper/75">
              {product.unlock_hint ||
                "Unlock through the host’s Vault to view full details."}
            </p>
            <Link href={vaultHref}>
              <Button size="sm">Unlock Vault</Button>
            </Link>
          </div>
        </div>
      </article>
    );
  }

  return (
    <article
      className={cn(
        "group flex h-full flex-col overflow-hidden rounded-[var(--radius-lg)] border border-primary/25 bg-ink text-paper sm:min-w-0",
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
          />
        )}
        <div className="absolute left-3 top-3">
          <Badge tone="accent" size="sm">
            Vault
          </Badge>
        </div>
      </Link>
      <div className={MARKETPLACE_CARD_BODY}>
        <h3 className={MARKETPLACE_CARD_TITLE}>
          <Link href={href} className="hover:text-primary">
            {product.name}
          </Link>
        </h3>
        {product.host_name ? (
          <p className="truncate text-sm text-paper/60">{product.host_name}</p>
        ) : null}
        <div className="mt-auto flex items-end justify-between gap-2 pt-1">
          <p className={MARKETPLACE_CARD_PRICE}>
            {formatNgn(Number(product.base_price))}
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
