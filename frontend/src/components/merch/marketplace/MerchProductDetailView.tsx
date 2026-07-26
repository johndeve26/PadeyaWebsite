"use client";

import Link from "next/link";
import { notFound, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { MerchAccessLockPanel } from "@/components/merch/MerchAccessLockPanel";
import { MarketplaceSectionGrid } from "@/components/merch/marketplace/MarketplaceSectionGrid";
import { MerchFallbackVisual } from "@/components/merch/MerchFallbackVisual";
import { MerchSizeGuideModal } from "@/components/merch/MerchSizeGuideModal";
import {
  Alert,
  Badge,
  Button,
  Container,
  Media,
  QuantityInput,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDate, formatDateTime, formatNgn } from "@/lib/format";
import {
  addBuyerCartItem,
  fetchMerchProductBySlug,
} from "@/lib/merch-api";
import { productImageUrl } from "@/lib/merch-fallback";
import { merchImageAlt } from "@/lib/seo/image-alt";
import {
  buildHostShopCheckoutHref,
  buildMerchCheckoutHref,
  productStockStatus,
  stockStatusLabel,
  variantAvailable,
} from "@/lib/merch-stock";
import type { MarketplaceProduct } from "@/lib/types/merch";

type Props = {
  slug: string;
  hostSlug?: string | null;
  /** Server-loaded product — missing products already 404 at the route. */
  initialProduct: MarketplaceProduct;
};

function dropAudienceLabel(audience?: string | null): string | null {
  switch ((audience || "").toLowerCase()) {
    case "ticket_buyers":
      return "Available to ticket buyers";
    case "checked_in":
      return "Available to checked-in fans";
    case "vip":
      return "VIP only";
    case "vault_members":
      return "Vault members only";
    case "public":
      return "Public drop";
    default:
      return null;
  }
}

export function MerchProductDetailView({
  slug,
  hostSlug: hostSlugProp,
  initialProduct,
}: Props) {
  const searchParams = useSearchParams();
  const hostSlug = hostSlugProp ?? searchParams.get("h");
  const { user } = useAuth();
  const toast = useToast();
  const [product, setProduct] = useState<MarketplaceProduct>(initialProduct);
  const [error, setError] = useState<string | null>(null);
  const [gone, setGone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [variantId, setVariantId] = useState(() => {
    return (
      initialProduct.variants.find((v) => variantAvailable(v) > 0)?.id ??
      initialProduct.variants[0]?.id ??
      ""
    );
  });
  const [quantity, setQuantity] = useState(1);
  const [adding, setAdding] = useState(false);
  const [checkingOut, setCheckingOut] = useState(false);
  const [sizeGuideOpen, setSizeGuideOpen] = useState(false);
  const [activeImage, setActiveImage] = useState(0);

  const maxQty = useMemo(() => {
    const selected = product.variants.find((v) => v.id === variantId);
    const selectedAvail = selected ? variantAvailable(selected) : 0;
    return Math.max(
      1,
      Math.min(
        selectedAvail || 1,
        product.max_per_order ?? product.max_per_buyer ?? (selectedAvail || 1),
      ),
    );
  }, [product, variantId]);

  // Clamp quantity during render when the available max changes (variant
  // switch or stock change) — avoids a setState-in-effect cascading render.
  const [prevMaxQty, setPrevMaxQty] = useState(maxQty);
  if (maxQty !== prevMaxQty) {
    setPrevMaxQty(maxQty);
    const clamped = Math.min(maxQty, Math.max(1, quantity));
    if (clamped !== quantity) setQuantity(clamped);
  }

  useEffect(() => {
    let active = true;
    const sameProduct =
      initialProduct.slug === slug &&
      (!hostSlug ||
        !initialProduct.host_slug ||
        initialProduct.host_slug === hostSlug);
    if (sameProduct) {
      return () => {
        active = false;
      };
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- client nav refetch
    setLoading(true);
    void (async () => {
      try {
        const row = await fetchMerchProductBySlug(slug, hostSlug);
        if (!active) return;
        setProduct(row);
        setError(null);
        setGone(false);
        const first =
          row.variants.find((v) => variantAvailable(v) > 0)?.id ??
          row.variants[0]?.id ??
          "";
        setVariantId(first);
      } catch (err) {
        if (!active) return;
        if (err instanceof ApiError && err.status === 404) {
          setGone(true);
        } else {
          setError(
            err instanceof ApiError ? err.detail : "Could not load product",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [slug, hostSlug, initialProduct]);

  // Keep client state aligned when the server passes a refreshed initial product.
  const [prevInitialId, setPrevInitialId] = useState(initialProduct.id);
  if (initialProduct.id !== prevInitialId && initialProduct.slug === slug) {
    setPrevInitialId(initialProduct.id);
    setProduct(initialProduct);
    setGone(false);
    setError(null);
  }

  const gallery = useMemo(() => {
    const urls = [
      product.cover_image_url || product.image_url,
      ...(product.gallery_urls ?? []),
    ].filter((u): u is string => Boolean(u));
    return Array.from(new Set(urls));
  }, [product]);

  if (gone) {
    notFound();
  }

  if (loading) {
    return (
      <Container className="py-12">
        <SkeletonLoader lines={8} />
      </Container>
    );
  }

  if (error) {
    return (
      <Container className="py-16">
        <Alert tone="danger" title="Could not load merch">
          {error}
        </Alert>
      </Container>
    );
  }

  const locked = Boolean(
    product.access_locked || product.teaser_only || product.access_eligible === false,
  );
  const canPurchase = !locked && product.access_eligible !== false;
  const stock = productStockStatus(product);
  const soldOut = stock === "sold_out";
  const selected = product.variants.find((v) => v.id === variantId);
  const selectedAvail = selected ? variantAvailable(selected) : 0;
  const fromPrice = selected
    ? Number(selected.effective_price)
    : Number(product.base_price);
  const image = gallery[activeImage] || productImageUrl(product);
  const audience = dropAudienceLabel(product.audience);
  const hostPath =
    product.host_shop_path ||
    (product.host_slug ? `/merch/hosts/${product.host_slug}` : null);
  const eventPath = product.event_slug
    ? `/events/${product.event_slug}`
    : null;

  const productPath =
    product.marketplace_path ||
    (hostSlug ? `/merch/hosts/${hostSlug}/${product.slug}` : `/merch/${product.slug}`);

  const checkoutHref =
    selected && !soldOut && canPurchase
      ? product.event_slug
        ? buildMerchCheckoutHref({
            eventSlug: product.event_slug,
            productId: product.id,
            variantId: selected.id,
            quantity,
          })
        : product.host_slug
          ? buildHostShopCheckoutHref({
              hostSlug: product.host_slug,
              productId: product.id,
              variantId: selected.id,
              quantity,
            })
          : null
      : null;

  const gatedCheckoutHref = checkoutHref
    ? user
      ? checkoutHref
      : `/login?next=${encodeURIComponent(checkoutHref)}`
    : null;

  async function onAddToCart() {
    if (!product || !selected || soldOut || !canPurchase) return;
    if (!user) {
      window.location.href = `/login?next=${encodeURIComponent(productPath)}`;
      return;
    }
    setAdding(true);
    try {
      await addBuyerCartItem(selected.id, quantity);
      toast.push({ tone: "success", title: "Added to cart" });
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Could not add to cart",
        description:
          err instanceof ApiError ? err.detail : "Please try again",
      });
    } finally {
      setAdding(false);
    }
  }

  async function onCheckout() {
    if (!product || !selected || soldOut || !canPurchase || !checkoutHref) return;
    if (!user) {
      window.location.href = gatedCheckoutHref!;
      return;
    }
    setCheckingOut(true);
    try {
      window.location.href = checkoutHref;
    } finally {
      setCheckingOut(false);
    }
  }

  const purchaseBusy = adding || checkingOut;

  return (
    <main className="min-w-0 overflow-x-clip bg-background pb-16">
      <Container className="py-8 sm:py-12">
        <div className="grid gap-8 lg:grid-cols-2 lg:gap-12">
          <div className="space-y-3">
            <div className="relative aspect-[4/5] overflow-hidden bg-ink">
              {image ? (
                <Media
                  src={image}
                  alt={merchImageAlt(product.name)}
                  className="h-full w-full object-cover"
                  priority
                  sizes="merchHero"
                />
              ) : (
                <MerchFallbackVisual
                  productType={product.product_type}
                  productName={product.name}
                  eventTitle={product.event_title}
                />
              )}
            </div>
            {gallery.length > 1 ? (
              <div className="flex gap-2 overflow-x-auto">
                {gallery.map((url, i) => (
                  <button
                    key={url}
                    type="button"
                    onClick={() => setActiveImage(i)}
                    className={`relative h-16 w-16 shrink-0 overflow-hidden ring-2 ${
                      i === activeImage ? "ring-primary" : "ring-transparent"
                    }`}
                  >
                    <Media
                      src={url}
                      alt={merchImageAlt(product.name, {
                        index: i,
                        total: gallery.length,
                      })}
                      className="h-full w-full object-cover"
                      sizes="merchThumb"
                    />
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          <div className="space-y-6">
            <div className="space-y-3">
              <div className="flex flex-wrap gap-1.5">
                {(product.badges ?? []).map((badge) => (
                  <Badge key={badge} tone="dark" size="sm">
                    {badge}
                  </Badge>
                ))}
              </div>
              <h1 className="text-3xl font-extrabold tracking-tight text-heading sm:text-4xl">
                {product.name}
              </h1>
              {product.host_name ? (
                <p className="text-base font-semibold text-muted-foreground">
                  {hostPath ? (
                    <Link href={hostPath} className="hover:text-primary">
                      {product.host_name}
                    </Link>
                  ) : (
                    product.host_name
                  )}
                </p>
              ) : null}
              <p className="text-2xl font-extrabold text-primary">
                {formatNgn(fromPrice)}
              </p>
              <p className="text-sm font-semibold text-muted-foreground">
                {stockStatusLabel(stock)}
              </p>
            </div>

            {product.short_description || product.description ? (
              <p className="text-base leading-relaxed text-muted-foreground">
                {product.short_description || product.description}
              </p>
            ) : null}

            {product.event_title && eventPath ? (
              <div className="space-y-2 border border-border bg-card p-4">
                <p className="text-sm font-extrabold text-foreground">
                  Linked event
                </p>
                <p className="text-base font-bold text-heading">
                  <Link href={eventPath} className="hover:text-primary">
                    {product.event_title}
                  </Link>
                </p>
                {product.event_start_at ? (
                  <p className="text-sm text-muted-foreground">
                    {formatDateTime(product.event_start_at)}
                  </p>
                ) : null}
                {product.event_location_label ? (
                  <p className="text-sm text-muted-foreground">
                    {product.event_location_label}
                  </p>
                ) : null}
              </div>
            ) : null}

            {(product.is_post_event_drop ||
              product.marketplace_kind === "post_event_drop") &&
            audience ? (
              <Alert tone="info" title="Drop eligibility">
                {audience}
                {product.post_event_drop_at
                  ? ` · Live ${formatDate(product.post_event_drop_at)}`
                  : null}
              </Alert>
            ) : null}

            {locked ? (
              <MerchAccessLockPanel product={product} />
            ) : (
              <div className="space-y-4">
                {product.variants.length > 0 ? (
                  <label className="block space-y-1.5 text-sm">
                    <span className="font-bold text-foreground">Variant</span>
                    <select
                      className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5"
                      value={variantId}
                      onChange={(e) => setVariantId(e.target.value)}
                    >
                      {product.variants.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.label} · {formatNgn(v.effective_price)}
                          {variantAvailable(v) <= 0 ? " (sold out)" : ""}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}

                <label className="block space-y-1.5 text-sm">
                  <span className="font-bold text-foreground">Quantity</span>
                  <QuantityInput
                    value={quantity}
                    min={1}
                    max={maxQty}
                    disabled={soldOut || !canPurchase}
                    onChange={setQuantity}
                  />
                </label>

                <div className="flex flex-wrap gap-2 text-xs font-semibold text-muted-foreground">
                  {product.pickup_enabled !== false ? (
                    <span>Pickup available</span>
                  ) : null}
                  {product.shipping_enabled ? <span>· Delivery</span> : null}
                </div>

                {product.pickup_instructions ||
                product.pickup_location_label ||
                product.pickup_time_window ? (
                  <div className="space-y-1 text-sm text-muted-foreground">
                    {product.pickup_location_label ? (
                      <p>Pickup: {product.pickup_location_label}</p>
                    ) : null}
                    {product.pickup_time_window ? (
                      <p>Window: {product.pickup_time_window}</p>
                    ) : null}
                    {product.pickup_instructions ? (
                      <p>{product.pickup_instructions}</p>
                    ) : null}
                  </div>
                ) : null}

                {product.size_chart ? (
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => setSizeGuideOpen(true)}
                  >
                    Size guide
                  </Button>
                ) : null}
              </div>
            )}

            <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              {locked &&
              (product.is_vault_exclusive || product.requires_vault_access) ? (
                <Link href="/dashboard/vault" className="w-full sm:w-auto">
                  <Button size="lg" className="w-full sm:w-auto">
                    Unlock Vault
                  </Button>
                </Link>
              ) : locked && eventPath ? (
                <Link href={eventPath} className="w-full sm:w-auto">
                  <Button size="lg" className="w-full sm:w-auto">
                    View event
                  </Button>
                </Link>
              ) : (
                <>
                  <Button
                    size="lg"
                    className="w-full sm:w-auto"
                    disabled={
                      soldOut ||
                      !selected ||
                      selectedAvail <= 0 ||
                      purchaseBusy
                    }
                    onClick={() => void onAddToCart()}
                  >
                    {adding ? "Adding…" : soldOut ? "Sold out" : "Add to cart"}
                  </Button>
                  {checkoutHref && gatedCheckoutHref ? (
                    <Button
                      size="lg"
                      variant="secondary"
                      className="w-full sm:w-auto"
                      disabled={
                        soldOut ||
                        !selected ||
                        selectedAvail <= 0 ||
                        purchaseBusy
                      }
                      onClick={() => void onCheckout()}
                    >
                      {checkingOut ? "Opening…" : "Checkout"}
                    </Button>
                  ) : null}
                </>
              )}
              {hostPath ? (
                <Link href={hostPath} className="w-full sm:w-auto">
                  <Button
                    size="lg"
                    variant="secondary"
                    className="w-full sm:w-auto"
                  >
                    Host shop
                  </Button>
                </Link>
              ) : null}
            </div>

            <div className="flex flex-wrap gap-3 text-sm font-semibold">
              <Link href="/help" className="text-primary hover:underline">
                Help
              </Link>
              <Link href="/support" className="text-primary hover:underline">
                Support
              </Link>
              <Link
                href="/refund-policy"
                className="text-primary hover:underline"
              >
                Refund policy
              </Link>
            </div>
          </div>
        </div>

        {(product.more_by_host?.length ?? 0) > 0 ? (
          <section className="mt-16">
            <h2 className="mb-5 text-2xl font-extrabold tracking-tight text-heading">
              More by {product.host_name || "this host"}
            </h2>
            <MarketplaceSectionGrid
              products={product.more_by_host ?? []}
              label={`More by ${product.host_name || "this host"}`}
            />
          </section>
        ) : null}
      </Container>

      {product.size_chart ? (
        <MerchSizeGuideModal
          open={sizeGuideOpen}
          onClose={() => setSizeGuideOpen(false)}
          chart={product.size_chart}
        />
      ) : null}
    </main>
  );
}
