"use client";

import Link from "next/link";

import { MerchFallbackVisual } from "@/components/merch/MerchFallbackVisual";
import { Badge, Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import { productImageUrl } from "@/lib/merch-fallback";
import type { MarketplaceHostShop } from "@/lib/types/merch";

type Props = {
  shop: MarketplaceHostShop;
  className?: string;
};

function hostInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

function resolveBadges(shop: MarketplaceHostShop): string[] {
  if (shop.shop_badges?.length) return shop.shop_badges;
  const kinds = new Set(
    (shop.latest_products ?? [])
      .map((p) => p.marketplace_kind)
      .filter(Boolean),
  );
  const badges: string[] = [];
  if (kinds.has("standalone")) badges.push("Standalone");
  if (kinds.has("event_merch") || kinds.has("event_addon"))
    badges.push("Event merch");
  if (kinds.has("vault_exclusive")) badges.push("Vault");
  if (kinds.has("post_event_drop")) badges.push("Drops");
  return badges;
}

export function MarketplaceHostShopCard({ shop, className }: Props) {
  const username = shop.host_slug || shop.host_username || "";
  const href = shop.shop_path || `/merch/hosts/${username}`;
  const thumbs = (shop.latest_products ?? []).slice(0, 3);
  const badges = resolveBadges(shop);
  const avatar = shop.host_avatar_url;

  return (
    <article
      className={cn(
        "flex h-full flex-col gap-3 rounded-[var(--radius-lg)] border border-border bg-card p-4 dark:bg-surface-elevated sm:min-w-0",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        {avatar ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={avatar}
            alt=""
            className="size-12 shrink-0 rounded-full object-cover ring-2 ring-border"
          />
        ) : (
          <div
            aria-hidden
            className="flex size-12 shrink-0 items-center justify-center rounded-full bg-ink text-sm font-extrabold text-primary"
          >
            {hostInitials(shop.host_name)}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-lg font-extrabold tracking-tight text-heading">
            <Link href={href} className="hover:text-primary-text">
              {shop.host_name}
            </Link>
          </h3>
          <p className="mt-0.5 text-sm font-semibold text-muted-foreground">
            @{username}
          </p>
          <p className="mt-1 text-xs font-bold text-primary">
            {shop.merch_count} products
          </p>
        </div>
      </div>

      {badges.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {badges.map((b) => (
            <Badge key={b} tone="outline" size="sm">
              {b}
            </Badge>
          ))}
        </div>
      ) : null}

      {thumbs.length > 0 ? (
        <div className="grid grid-cols-3 gap-2">
          {thumbs.map((product) => {
            const image = productImageUrl(product);
            return (
              <div
                key={product.id}
                className="aspect-square overflow-hidden rounded-md bg-muted"
              >
                {image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={image}
                    alt=""
                    loading="lazy"
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <MerchFallbackVisual
                    productType={product.product_type}
                    productName={product.name}
                    category={product.category}
                    compact
                  />
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="aspect-square rounded-md bg-muted/60"
              aria-hidden
            />
          ))}
        </div>
      )}

      <div className="mt-auto">
        <Link href={href}>
          <Button size="sm" variant="primary" className="w-full">
            Visit shop
          </Button>
        </Link>
      </div>
    </article>
  );
}
