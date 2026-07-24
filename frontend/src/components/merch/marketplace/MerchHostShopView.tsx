"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { MarketplaceEmptyState } from "@/components/merch/marketplace/MarketplaceEmptyState";
import { MarketplaceShopGrid } from "@/components/merch/marketplace/MarketplaceShopGrid";
import { Alert, Badge, Button, Container, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMerchHostShop } from "@/lib/merch-api";
import type { MarketplaceHostShopDetail } from "@/lib/types/merch";

type Props = {
  username: string;
  initialShop?: MarketplaceHostShopDetail | null;
};

export function MerchHostShopView({ username, initialShop = null }: Props) {
  const [shop, setShop] = useState<MarketplaceHostShopDetail | null>(
    initialShop,
  );
  const [loading, setLoading] = useState(!initialShop);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await fetchMerchHostShop(username);
        if (cancelled) return;
        setShop(data);
        setError(null);
        setNotFound(false);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        } else {
          setError(
            err instanceof ApiError ? err.detail : "Could not load host shop",
          );
        }
        setShop(null);
      } finally {
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [username, initialShop]);

  const hostName =
    shop?.host_name ||
    shop?.host?.display_name ||
    shop?.host?.name ||
    username;
  const hostSlug =
    shop?.host_slug ||
    shop?.host_username ||
    shop?.host?.slug ||
    shop?.host?.username ||
    username;
  const products = shop?.products ?? [];

  return (
    <main className="min-w-0 overflow-x-clip pb-16">
      <section className="bg-ink py-14 text-paper sm:py-20">
        <Container>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary">
            Host shop
          </p>
          {loading ? (
            <div className="mt-4 max-w-md">
              <SkeletonLoader lines={3} />
            </div>
          ) : (
            <>
              <h1 className="mt-3 text-balance text-3xl font-extrabold tracking-tight sm:text-5xl">
                {hostName}
              </h1>
              <p className="mt-2 text-sm font-semibold text-paper/55">
                @{hostSlug}
              </p>
              {shop?.storefront_description ||
              shop?.storefront_title ? (
                <p className="mt-4 max-w-xl text-base leading-relaxed text-paper/70">
                  {shop.storefront_description ||
                    shop.storefront_title}
                </p>
              ) : (
                <p className="mt-4 max-w-xl text-base leading-relaxed text-paper/70">
                  Official merch from this Pàdéyá host.
                </p>
              )}
              <div className="mt-5 flex flex-wrap items-center gap-3">
                <Badge tone="accent" size="md">
                  {shop?.product_count ?? products.length} products
                </Badge>
                <Link href={`/u/${hostSlug}`}>
                  <Button variant="outline-dark" size="sm">
                    Host profile
                  </Button>
                </Link>
                <Link href={`/u/${hostSlug}/merch`}>
                  <Button variant="ghost" size="sm" className="text-paper">
                    Classic storefront
                  </Button>
                </Link>
              </div>
            </>
          )}
        </Container>
      </section>

      <Container className="mt-10 sm:mt-14">
        {notFound ? (
          <Alert tone="danger" title="Shop not found">
            This host shop is unavailable.
          </Alert>
        ) : null}
        {error ? (
          <Alert tone="danger" title="Could not load shop">
            {error}
          </Alert>
        ) : null}
        <MarketplaceShopGrid
          products={products}
          loading={loading}
          skeletonCount={8}
          empty={
            <MarketplaceEmptyState
              title={
                shop?.empty_message || "This host has not added merch yet."
              }
            />
          }
        />
      </Container>
    </main>
  );
}
