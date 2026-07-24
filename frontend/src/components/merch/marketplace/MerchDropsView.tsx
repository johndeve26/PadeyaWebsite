"use client";

import { useEffect, useState } from "react";

import { MarketplaceEmptyState } from "@/components/merch/marketplace/MarketplaceEmptyState";
import { MarketplaceSectionGrid } from "@/components/merch/marketplace/MarketplaceSectionGrid";
import { Alert, Container } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { brand } from "@/lib/brand";
import { fetchMerchDrops } from "@/lib/merch-api";
import type { MarketplaceProduct } from "@/lib/types/merch";

export function MerchDropsView() {
  const [items, setItems] = useState<MarketplaceProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const result = await fetchMerchDrops(48);
        if (active) {
          setItems(result.items);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Could not load drops",
          );
          setItems([]);
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="min-w-0 overflow-x-clip pb-16">
      <section className="bg-ink py-14 text-paper sm:py-20">
        <Container>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary">
            Post-event drops · {brand.name}
          </p>
          <h1 className="mt-3 max-w-3xl text-balance text-3xl font-extrabold tracking-tight sm:text-5xl">
            Limited drops after the night.
          </h1>
          <p className="mt-4 max-w-xl text-base leading-relaxed text-paper/70 sm:text-lg">
            Ticket buyers, checked-in fans, VIP, and Vault members can unlock
            exclusive post-event merch when hosts go live.
          </p>
        </Container>
      </section>

      <Container className="mt-10 sm:mt-14">
        {error ? (
          <Alert tone="danger" title="Could not load drops">
            {error}
          </Alert>
        ) : null}
        <MarketplaceSectionGrid
          products={items}
          loading={loading}
          skeletonCount={6}
          variant="drops"
          label="Post-event drops"
          empty={
            <MarketplaceEmptyState title="No post-event drops available yet." />
          }
        />
      </Container>
    </main>
  );
}
