"use client";

import { useEffect, useMemo, useState } from "react";

import { EventMerchDetailModal } from "@/components/merch/EventMerchDetailModal";
import { MerchBundleCard } from "@/components/merch/MerchBundleCard";
import { MerchEmptyState } from "@/components/merch/MerchEmptyState";
import {
  MerchFilterChips,
  type MerchFilterKey,
} from "@/components/merch/MerchFilterChips";
import {
  MerchProductCard,
  primaryMerchCtaLabel,
} from "@/components/merch/MerchProductCard";
import { MerchProductGrid } from "@/components/merch/MerchProductGrid";
import { SkeletonLoader, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  readMerchDraftCart,
  upsertMerchDraftLine,
  writeMerchDraftCart,
  type MerchDraftCart,
} from "@/lib/merch-draft-cart";
import { productImageUrl } from "@/lib/merch-fallback";
import { fetchEventBundles, fetchMerchCatalog } from "@/lib/merch-api";
import {
  productStockStatus,
  variantAvailable,
} from "@/lib/merch-stock";
import type { MerchBundle, MerchCatalogProduct } from "@/lib/types/merch";

type Props = {
  eventId: string;
  eventSlug: string;
  eventTitle: string;
  hostId?: string | null;
  hostName?: string | null;
  hostSlug?: string | null;
  referralCode?: string;
  compact?: boolean;
  /** When provided, skip internal fetch. */
  products?: MerchCatalogProduct[] | null;
  onProductsLoaded?: (products: MerchCatalogProduct[]) => void;
  cart?: MerchDraftCart | null;
  onCartChange?: (cart: MerchDraftCart) => void;
  showFilters?: boolean;
  showBundles?: boolean;
  onMetaChange?: (meta: {
    hasShipping: boolean;
    hasVault: boolean;
    hasLowStock: boolean;
    productCount: number;
  }) => void;
};

function productLocked(product: MerchCatalogProduct) {
  return Boolean(
    product.access_locked || product.teaser_only || !product.access_eligible,
  );
}

function matchesFilter(
  product: MerchCatalogProduct,
  filter: MerchFilterKey,
): boolean {
  if (filter === "all" || filter === "bundles") return true;
  const locked = productLocked(product);
  const status = productStockStatus(product);
  switch (filter) {
    case "available":
      return !locked && status === "available";
    case "pickup":
      return product.pickup_enabled !== false;
    case "shipping":
      return Boolean(product.shipping_enabled);
    case "vault":
      return Boolean(
        product.is_vault_exclusive || product.requires_vault_access,
      );
    case "ticket":
      return Boolean(
        product.requires_ticket ||
          product.required_access_type === "ticket" ||
          product.required_access_type === "vip" ||
          product.required_access_type === "check_in",
      );
    case "low_stock":
      return !locked && status === "low_stock";
    case "sponsor":
      return Boolean(product.is_sponsor_branded);
    case "post_event":
      return Boolean(product.is_post_event_drop);
    default:
      return true;
  }
}

export function EventMerchCatalog({
  eventId,
  eventSlug,
  eventTitle,
  hostId,
  hostName,
  hostSlug,
  referralCode,
  compact = false,
  products: productsProp,
  onProductsLoaded,
  cart: cartProp,
  onCartChange,
  showFilters = !compact,
  showBundles = !compact,
  onMetaChange,
}: Props) {
  const toast = useToast();
  const [fetched, setFetched] = useState<MerchCatalogProduct[] | null>(null);
  const [bundles, setBundles] = useState<MerchBundle[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<MerchCatalogProduct | null>(null);
  const [filter, setFilter] = useState<MerchFilterKey>("all");
  const [localCart, setLocalCart] = useState<MerchDraftCart | null>(null);

  const controlled = productsProp !== undefined;
  const cartControlled = cartProp !== undefined;
  const cart = cartControlled
    ? (cartProp ?? null)
    : (localCart ?? readMerchDraftCart(eventId));

  useEffect(() => {
    if (controlled) return;
    let active = true;
    void (async () => {
      try {
        const rows = await fetchMerchCatalog(eventId);
        if (!active) return;
        setFetched(rows);
        onProductsLoaded?.(rows);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError ? err.detail : "Could not load merch",
        );
        setFetched([]);
        onProductsLoaded?.([]);
      }
    })();
    return () => {
      active = false;
    };
  }, [controlled, eventId, onProductsLoaded]);

  const skipBundles = !showBundles || compact;

  useEffect(() => {
    if (skipBundles) return;
    let active = true;
    void fetchEventBundles(eventId)
      .then((rows) => {
        if (!active) return;
        setBundles(rows.filter((b) => b.status === "active"));
      })
      .catch(() => {
        if (active) setBundles([]);
      });
    return () => {
      active = false;
    };
  }, [eventId, skipBundles]);

  const products = controlled ? productsProp : fetched;
  const activeBundles = skipBundles ? [] : (bundles ?? []);
  const bundlesLoading = !skipBundles && bundles === null;

  const visible = useMemo(() => {
    const rows = products ?? [];
    return rows
      .filter((p) => (compact ? p.show_on_event_page !== false : true))
      .filter((p) => matchesFilter(p, filter))
      .sort(
        (a, b) =>
          Number(Boolean(b.is_featured)) - Number(Boolean(a.is_featured)),
      );
  }, [compact, filter, products]);

  useEffect(() => {
    if (!products || !onMetaChange) return;
    const rows = products;
    onMetaChange({
      hasShipping: rows.some((p) => p.shipping_enabled),
      hasVault: rows.some(
        (p) => p.is_vault_exclusive || p.requires_vault_access,
      ),
      hasLowStock: rows.some(
        (p) => !productLocked(p) && productStockStatus(p) === "low_stock",
      ),
      productCount: rows.length,
    });
  }, [onMetaChange, products]);

  function commitCart(next: MerchDraftCart) {
    writeMerchDraftCart(next);
    if (!cartControlled) setLocalCart(next);
    onCartChange?.(next);
  }

  function addSingleVariant(product: MerchCatalogProduct) {
    const variant =
      product.variants.find((v) => variantAvailable(v) > 0) ??
      product.variants[0];
    if (!variant) return;
    const base: MerchDraftCart = cart ?? {
      eventId,
      eventSlug,
      lines: [],
      updatedAt: new Date().toISOString(),
    };
    const existing = base.lines.find((l) => l.variantId === variant.id);
    const nextQty = (existing?.quantity ?? 0) + 1;
    const max = Math.min(
      variantAvailable(variant),
      product.max_per_order ?? product.max_per_buyer ?? 10,
    );
    if (nextQty > max) {
      toast.push({
        tone: "warning",
        title: "Quantity limit reached",
      });
      return;
    }
    const next = upsertMerchDraftLine(base, {
      productId: product.id,
      variantId: variant.id,
      productName: product.name,
      variantLabel: variant.label,
      unitPrice: Number(variant.effective_price),
      quantity: nextQty,
      imageUrl: productImageUrl(product),
      productType: product.product_type,
    });
    commitCart(next);
    toast.push({ tone: "success", title: "Added to cart" });
  }

  function handlePrimary(product: MerchCatalogProduct) {
    const label = primaryMerchCtaLabel(product);
    if (
      label === "How to unlock" ||
      label === "Get eligible" ||
      label === "Unlock access" ||
      label === "Choose options"
    ) {
      setDetail(product);
      return;
    }
    if (label === "Sold out") return;
    addSingleVariant(product);
  }

  if (products === null || bundlesLoading) {
    return <SkeletonLoader lines={compact ? 2 : 5} />;
  }

  if (error) {
    return <p className="text-sm text-muted-foreground">{error}</p>;
  }

  const showBundleSection =
    showBundles &&
    !compact &&
    activeBundles.length > 0 &&
    (filter === "all" || filter === "bundles");
  const showProductGrid = filter !== "bundles";
  const listed = compact ? visible.slice(0, 3) : visible;

  const catalogEmpty =
    !compact &&
    (products ?? []).length === 0 &&
    activeBundles.length === 0;

  if (catalogEmpty) {
    const isDev = process.env.NODE_ENV === "development";
    return (
      <MerchEmptyState
        eventSlug={eventSlug}
        isDev={isDev}
        diagnostics={
          isDev
            ? [
                "API returned no products",
                "Products may be locked",
                "Storefront may be disabled",
                "No active variants",
                "Outside sales window",
              ]
            : undefined
        }
      />
    );
  }

  if (
    !compact &&
    !showBundleSection &&
    showProductGrid &&
    listed.length === 0
  ) {
    return (
      <div className="space-y-4">
        {showFilters ? (
          <MerchFilterChips
            value={filter}
            onChange={setFilter}
            hiddenKeys={activeBundles.length === 0 ? ["bundles"] : undefined}
          />
        ) : null}
        <p className="text-sm text-muted-foreground">
          No merch matches this filter.
        </p>
      </div>
    );
  }

  if (compact && listed.length === 0) return null;

  return (
    <div className={compact ? "space-y-4" : "space-y-8"}>
      {!compact && showFilters ? (
        <MerchFilterChips
          value={filter}
          onChange={setFilter}
          hiddenKeys={activeBundles.length === 0 ? ["bundles"] : undefined}
        />
      ) : null}

      {showBundleSection ? (
        <section className="space-y-4">
          <div>
            <h2 className="text-lg font-extrabold tracking-tight text-foreground sm:text-xl">
              Ticket + merch packs
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Bundle a ticket with official merch and save at checkout.
            </p>
          </div>
          <ul className="grid gap-4 sm:grid-cols-2">
            {activeBundles.map((bundle) => (
              <li key={bundle.id}>
                <MerchBundleCard
                  bundle={bundle}
                  eventSlug={eventSlug}
                  referralCode={referralCode}
                />
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {showProductGrid && listed.length > 0 ? (
        <section className="space-y-4">
          {!compact ? (
            <div>
              <h2 className="text-lg font-extrabold tracking-tight text-foreground sm:text-xl">
                Official merch
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Browse items for this event. Pickup at the venue unless a
                product ships.
              </p>
            </div>
          ) : null}

          <MerchProductGrid compact={compact}>
            {listed.map((product, index) => (
              <li
                key={product.id}
                className={
                  compact && index === 2 ? "hidden lg:list-item" : undefined
                }
              >
                <MerchProductCard
                  product={product}
                  eventTitle={eventTitle}
                  compact={compact}
                  onViewDetails={() => setDetail(product)}
                  onPrimaryAction={() => handlePrimary(product)}
                />
              </li>
            ))}
          </MerchProductGrid>
        </section>
      ) : null}

      <EventMerchDetailModal
        open={Boolean(detail)}
        onClose={() => setDetail(null)}
        product={detail}
        eventId={eventId}
        eventSlug={eventSlug}
        eventTitle={eventTitle}
        hostId={hostId}
        hostName={hostName}
        hostSlug={hostSlug}
        referralCode={referralCode}
        onAdded={() => {
          if (detail && !productLocked(detail)) {
            /* Detail handles cart; refresh local if uncontrolled */
            if (!cartControlled) {
              setLocalCart(readMerchDraftCart(eventId));
            }
            onCartChange?.(
              readMerchDraftCart(eventId) ?? {
                eventId,
                eventSlug,
                lines: [],
                updatedAt: new Date().toISOString(),
              },
            );
          }
          setDetail(null);
        }}
      />
    </div>
  );
}
