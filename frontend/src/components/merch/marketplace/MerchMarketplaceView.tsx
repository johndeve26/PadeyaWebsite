"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { HomeCardCarousel } from "@/components/home/HomeCardCarousel";
import { LazyMarketplaceSection } from "@/components/merch/marketplace/LazyMarketplaceSection";
import { MarketplaceEmptyState } from "@/components/merch/marketplace/MarketplaceEmptyState";
import {
  type MarketplaceFiltersValue,
} from "@/components/merch/marketplace/MarketplaceFilters";
import { MarketplaceFiltersPanel } from "@/components/merch/marketplace/MarketplaceFiltersPanel";
import { MarketplaceHostShopCard } from "@/components/merch/marketplace/MarketplaceHostShopCard";
import { MarketplaceSectionGrid } from "@/components/merch/marketplace/MarketplaceSectionGrid";
import { MarketplaceShopGrid } from "@/components/merch/marketplace/MarketplaceShopGrid";
import { MerchCategoryChips } from "@/components/merch/marketplace/MerchCategoryChips";
import { MerchDiscoveryTabs } from "@/components/merch/marketplace/MerchDiscoveryTabs";
import { MerchMarketplaceHero } from "@/components/merch/marketplace/MerchMarketplaceHero";
import { MerchTypeCards } from "@/components/merch/marketplace/MerchTypeCards";
import { MerchFaqSection } from "@/components/marketing/merch/MerchFaqSection";
import { Alert, Button, Container, SkeletonCard } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  curateMarketplaceHome,
  excludeShown,
  markShown,
  MERCH_SECTION_LIMITS,
  type MerchDiscoveryTab,
} from "@/lib/merch/marketplace-curation";
import {
  fetchMerchMarketplace,
  fetchMerchMarketplaceHomeSynced,
} from "@/lib/merch-api";
import {
  MARKETPLACE_CAROUSEL_SLIDE,
  MARKETPLACE_HOST_SHOP_CAROUSEL_GRID,
  MARKETPLACE_PRODUCT_GRID,
} from "@/lib/merch/marketplace-layout";
import type { MarketplaceHome, MarketplaceProduct } from "@/lib/types/merch";

function SectionHeader({
  id,
  title,
  description,
  href,
  linkLabel,
}: {
  id?: string;
  title: string;
  description?: string;
  href?: string;
  linkLabel?: string;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2
          id={id}
          className="text-2xl font-extrabold tracking-tight text-heading sm:text-3xl"
        >
          {title}
        </h2>
        {description ? (
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
            {description}
          </p>
        ) : null}
      </div>
      {href && linkLabel ? (
        <Link href={href}>
          <Button variant="secondary" size="sm">
            {linkLabel}
          </Button>
        </Link>
      ) : null}
    </div>
  );
}

function parseFiltersFromSearch(
  params: URLSearchParams,
): MarketplaceFiltersValue {
  const type = params.get("type") ?? undefined;
  const category = params.get("category") ?? undefined;
  return {
    sort: "featured",
    ...(type ? { type } : {}),
    ...(category ? { category } : {}),
  };
}

export function MerchMarketplaceView() {
  const searchParams = useSearchParams();
  const [home, setHome] = useState<MarketplaceHome | null>(null);
  const [homeError, setHomeError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<MerchDiscoveryTab>("all");
  const [filters, setFilters] = useState<MarketplaceFiltersValue>(() =>
    parseFiltersFromSearch(searchParams),
  );
  const [catalog, setCatalog] = useState<MarketplaceProduct[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogLoadingMore, setCatalogLoadingMore] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [catalogTotal, setCatalogTotal] = useState(0);

  const curated = useMemo(
    () => (home ? curateMarketplaceHome(home) : null),
    [home],
  );

  const curatedProductKeys = useMemo(() => {
    if (!curated) return new Set<string>();
    const shown = new Set<string>();
    markShown(shown, curated.featured);
    markShown(shown, curated.eventMerch);
    return shown;
  }, [curated]);

  const catalogDisplay = useMemo(
    () => excludeShown(catalog, curatedProductKeys),
    [catalog, curatedProductKeys],
  );

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchMerchMarketplaceHomeSynced();
        if (active) {
          setHome(data);
          setHomeError(null);
        }
      } catch (err) {
        if (active) {
          setHomeError(
            err instanceof ApiError
              ? err.detail
              : "Could not load merch marketplace",
          );
          setHome({
            featured: [],
            event_merch: [],
            host_shops: [],
            drops: [],
            vault_exclusives: [],
            categories: [],
            empty: true,
          });
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const loadCatalog = useCallback(
    async (
      query: MarketplaceFiltersValue,
      options?: { append?: boolean; offset?: number },
    ) => {
      const append = options?.append ?? false;
      if (append) {
        setCatalogLoadingMore(true);
      } else {
        setCatalogLoading(true);
      }
      setCatalogError(null);
      try {
        const offset = append ? (options?.offset ?? 0) : 0;
        const result = await fetchMerchMarketplace({
          ...query,
          limit: MERCH_SECTION_LIMITS.catalogPage,
          offset,
        });
        setCatalog((prev) =>
          append ? [...prev, ...result.items] : result.items,
        );
        setCatalogTotal(result.total);
      } catch (err) {
        setCatalogError(
          err instanceof ApiError ? err.detail : "Could not load merch catalog",
        );
        if (!append) {
          setCatalog([]);
          setCatalogTotal(0);
        }
      } finally {
        setCatalogLoading(false);
        setCatalogLoadingMore(false);
      }
    },
    [],
  );

  useEffect(() => {
    const initial = parseFiltersFromSearch(searchParams);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sync catalog with URL + initial fetch
    setFilters((prev) => ({ ...prev, ...initial }));
    void loadCatalog(initial);
  }, [loadCatalog, searchParams]);

  const loadingHome = home === null;
  const hasMoreCatalog = catalog.length < catalogTotal;

  function applyFilters() {
    void loadCatalog(filters);
    document.getElementById("catalog")?.scrollIntoView({ behavior: "smooth" });
  }

  function selectCategory(slug: string) {
    const next = { ...filters, category: slug, sort: "featured" as const };
    setFilters(next);
    void loadCatalog(next);
    document.getElementById("catalog")?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <main className="min-w-0 overflow-x-clip pb-16">
      <MerchMarketplaceHero catalogHref="#catalog" />

      {homeError ? (
        <Container className="mt-8">
          <Alert tone="warning" title="Marketplace partially unavailable">
            {homeError}
          </Alert>
        </Container>
      ) : null}

      <Container className="mt-8 sm:mt-10">
        <MerchDiscoveryTabs
          active={activeTab}
          onChange={(tab) => {
            setActiveTab(tab);
            if (tab === "bundles") {
              const next = { ...filters, type: "bundle", sort: "featured" as const };
              setFilters(next);
              void loadCatalog(next);
            }
          }}
        />
      </Container>

      <Container className="mt-10 space-y-11 sm:mt-12 sm:space-y-12">
        <section aria-labelledby="featured-heading">
          <SectionHeader
            id="featured-heading"
            title="Featured merch"
            description="Curated picks from Pàdéyá hosts — limited to our best sellers."
          />
          <MarketplaceSectionGrid
            products={curated?.featured ?? []}
            loading={loadingHome}
            limit={MERCH_SECTION_LIMITS.featured}
            skeletonCount={4}
            empty={
              <MarketplaceEmptyState title="No featured merch yet." />
            }
          />
        </section>

        <section aria-labelledby="merch-types-heading">
          <SectionHeader
            id="merch-types-heading"
            title="Shop by merch type"
            description="Understand how standalone shops, event add-ons, drops, Vault, and bundles fit together."
          />
          <MerchTypeCards />
        </section>

        <LazyMarketplaceSection eager>
          <section id="event-merch" aria-labelledby="event-merch-heading">
            <SectionHeader
              id="event-merch-heading"
              title="Event merch"
              description="Products attached to upcoming and live nights — with event context on every card."
              href="/merch?type=event_merch#catalog"
              linkLabel="View all event merch"
            />
            <MarketplaceSectionGrid
              products={curated?.eventMerch ?? []}
              loading={loadingHome}
              limit={MERCH_SECTION_LIMITS.eventMerch}
              skeletonCount={4}
              empty={
                <MarketplaceEmptyState title="No event merch available yet." />
              }
            />
          </section>
        </LazyMarketplaceSection>

        <LazyMarketplaceSection>
          <section id="host-shops" aria-labelledby="host-shops-heading">
            <SectionHeader
              id="host-shops-heading"
              title="Host shops"
              description="Browse standalone merch from hosts with active storefronts."
            />
            {loadingHome ? (
              <div className={MARKETPLACE_PRODUCT_GRID}>
                {Array.from({ length: 3 }).map((_, i) => (
                  <SkeletonCard key={i} />
                ))}
              </div>
            ) : (curated?.hostShops?.length ?? 0) === 0 ? (
              <MarketplaceEmptyState
                title="No host shops are live yet."
                description="When hosts publish standalone merch, their shops will appear here."
                action={
                  <Link href="#catalog">
                    <Button size="sm">Explore all merch</Button>
                  </Link>
                }
              />
            ) : (
              <HomeCardCarousel
                label="Host shops"
                until="sm"
                desktopGridClassName={MARKETPLACE_HOST_SHOP_CAROUSEL_GRID}
                slideClassName={MARKETPLACE_CAROUSEL_SLIDE}
              >
                {curated?.hostShops.map((shop) => (
                  <div key={shop.host_id} className="min-w-0 h-full">
                    <MarketplaceHostShopCard shop={shop} />
                  </div>
                ))}
              </HomeCardCarousel>
            )}
          </section>
        </LazyMarketplaceSection>

        <LazyMarketplaceSection>
          <section id="drops" aria-labelledby="drops-heading">
            <SectionHeader
              id="drops-heading"
              title="Post-event drops"
              description="Limited releases with eligibility rules — for fans who were there or bought in."
              href="/merch/drops"
              linkLabel="All drops"
            />
            <MarketplaceSectionGrid
              products={curated?.drops ?? []}
              loading={loadingHome}
              variant="drops"
              limit={MERCH_SECTION_LIMITS.drops}
              skeletonCount={4}
              empty={
                <MarketplaceEmptyState title="No post-event drops live yet." />
              }
            />
          </section>
        </LazyMarketplaceSection>

        <LazyMarketplaceSection>
          <section id="vault" aria-labelledby="vault-heading">
            <SectionHeader
              id="vault-heading"
              title="Vault exclusives"
              description="Premium merch unlocked through a host’s Vault — teasers only until you have access."
              href="/merch/vault"
              linkLabel="Vault shop"
            />
            <MarketplaceSectionGrid
              products={curated?.vault ?? []}
              loading={loadingHome}
              variant="vault"
              limit={MERCH_SECTION_LIMITS.vault}
              skeletonCount={4}
              empty={
                <MarketplaceEmptyState title="No Vault exclusives listed yet." />
              }
            />
          </section>
        </LazyMarketplaceSection>

        <LazyMarketplaceSection>
          <section aria-labelledby="categories-heading">
            <SectionHeader
              id="categories-heading"
              title="Categories"
              description="Browse by product type — apparel, caps, posters, bundles, and more."
            />
            <MerchCategoryChips
              categories={home?.categories}
              activeCategory={filters.category}
              onSelect={selectCategory}
            />
          </section>
        </LazyMarketplaceSection>

        <section
          id="catalog"
          aria-labelledby="catalog-heading"
          className="scroll-mt-24"
        >
          <SectionHeader
            id="catalog-heading"
            title="Shop all merch"
            description={
              catalogTotal > 0
                ? `Showing ${catalogDisplay.length} of ${catalogTotal} products${curatedProductKeys.size ? " (featured & event picks may also appear above)" : ""}.`
                : "Filter by keyword, host, category, price, and more."
            }
          />
          <div className="mb-6">
            <MarketplaceFiltersPanel
              value={filters}
              onChange={setFilters}
              onSubmit={applyFilters}
            />
          </div>
          {catalogError ? (
            <Alert tone="danger" title="Could not load catalog" className="mb-6">
              {catalogError}
            </Alert>
          ) : null}
          <MarketplaceShopGrid
            products={catalogDisplay}
            loading={catalogLoading}
            loadingMore={catalogLoadingMore}
            hasMore={hasMoreCatalog}
            onLoadMore={() =>
              void loadCatalog(filters, { append: true, offset: catalog.length })
            }
            skeletonCount={MERCH_SECTION_LIMITS.catalogPage}
            empty={
              <MarketplaceEmptyState title="No merch matches these filters." />
            }
          />
        </section>
      </Container>

      <div className="mt-14 sm:mt-16">
        <MerchFaqSection />
      </div>
    </main>
  );
}
