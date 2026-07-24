"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { MerchAccessLockPanel } from "@/components/merch/MerchAccessLockPanel";
import { MerchFallbackVisual } from "@/components/merch/MerchFallbackVisual";
import { MerchSizeGuideModal } from "@/components/merch/MerchSizeGuideModal";
import { ReportMerchDialog } from "@/components/merch/ReportMerchDialog";
import { SponsorBrandedMark } from "@/components/merch/SponsorBrandedMark";
import { Badge, Button, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  trackMerchProductViewed,
  trackMerchVariantSelected,
  trackMerchVaultExclusiveViewed,
} from "@/lib/analytics";
import { formatNgn } from "@/lib/format";
import {
  fetchProductReviews,
  reportMerchProduct,
  type MerchReviewPublic,
} from "@/lib/merch-api";
import {
  readMerchDraftCart,
  upsertMerchDraftLine,
  writeMerchDraftCart,
} from "@/lib/merch-draft-cart";
import { productImageUrl } from "@/lib/merch-fallback";
import {
  buildMerchCheckoutHref,
  stockStatus,
  stockStatusLabel,
  variantAvailable,
} from "@/lib/merch-stock";
import type { MerchCatalogProduct } from "@/lib/types/merch";

type Props = {
  product: MerchCatalogProduct;
  eventId: string;
  eventSlug: string;
  eventTitle: string;
  hostId?: string | null;
  hostName?: string | null;
  hostSlug?: string | null;
  referralCode?: string;
  onAdded?: () => void;
  /** Hide link to dedicated product page (already on that page). */
  showFullPageLink?: boolean;
  /** Fixed bottom purchase bar — use on full pages, not inside modals. */
  stickyPurchaseBar?: boolean;
};

export function EventMerchDetail({
  product,
  eventId,
  eventSlug,
  eventTitle,
  hostId,
  hostName,
  hostSlug,
  referralCode,
  onAdded,
  showFullPageLink = true,
  stickyPurchaseBar = true,
}: Props) {
  const { user } = useAuth();
  const toast = useToast();
  const [reportOpen, setReportOpen] = useState(false);
  const [sizeGuideOpen, setSizeGuideOpen] = useState(false);
  const viewedRef = useRef(false);
  const gallery = useMemo(() => {
    const urls = [
      product.cover_image_url || product.image_url,
      ...(product.gallery_urls ?? []),
    ].filter((u): u is string => Boolean(u));
    return Array.from(new Set(urls));
  }, [product]);

  const [activeImage, setActiveImage] = useState(0);
  const [variantId, setVariantId] = useState(
    product.variants.find((v) => variantAvailable(v) > 0)?.id ??
      product.variants[0]?.id ??
      "",
  );
  const [quantity, setQuantity] = useState(1);
  const [reviews, setReviews] = useState<{
    average_rating: number | null;
    review_count: number;
    reviews: MerchReviewPublic[];
  } | null>(null);

  const locked = Boolean(
    product.access_locked || product.teaser_only || product.access_eligible === false,
  );
  const canPurchase = !locked && Boolean(product.access_eligible !== false);

  useEffect(() => {
    if (viewedRef.current) return;
    viewedRef.current = true;
    trackMerchProductViewed({
      targetEventId: eventId,
      hostId: hostId ?? undefined,
      merchProductId: product.id,
    });
    if (product.is_vault_exclusive || product.requires_vault_access) {
      trackMerchVaultExclusiveViewed({
        targetEventId: eventId,
        hostId: hostId ?? undefined,
        merchProductId: product.id,
        vaultLocked: locked,
      });
    }
  }, [
    eventId,
    hostId,
    product.id,
    product.is_vault_exclusive,
    product.requires_vault_access,
    locked,
  ]);

  useEffect(() => {
    if (locked) return;
    let active = true;
    void (async () => {
      const data = await fetchProductReviews(product.id).catch(() => null);
      if (active) setReviews(data);
    })();
    return () => {
      active = false;
    };
  }, [product.id, locked]);

  const visibleReviews = locked ? null : reviews;

  const variant =
    product.variants.find((v) => v.id === variantId) ?? product.variants[0];
  const available = variant ? variantAvailable(variant) : 0;
  const status = stockStatus(available);
  const maxQty = Math.min(
    available,
    product.max_per_order ?? product.max_per_buyer ?? 10,
  );
  const soldOut = !canPurchase || available <= 0;

  const checkoutHref =
    variant && !soldOut
      ? buildMerchCheckoutHref({
          eventSlug,
          productId: product.id,
          variantId: variant.id,
          quantity,
          referralCode,
        })
      : `/events/${eventSlug}/checkout`;
  const gatedCheckoutHref = user
    ? checkoutHref
    : `/login?next=${encodeURIComponent(checkoutHref)}`;

  function addToCart() {
    if (!variant || soldOut) return;
    const base =
      readMerchDraftCart(eventId) ?? {
        eventId,
        eventSlug,
        lines: [],
        updatedAt: new Date().toISOString(),
      };
    const existing = base.lines.find((l) => l.variantId === variant.id);
    const nextQty = (existing?.quantity ?? 0) + quantity;
    const max = Math.min(
      available,
      product.max_per_order ?? product.max_per_buyer ?? 10,
    );
    if (nextQty > max) {
      toast.push({ tone: "warning", title: "Quantity limit reached" });
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
    writeMerchDraftCart(next);
    toast.push({ tone: "success", title: "Added to cart" });
    onAdded?.();
  }

  return (
    <div
      className={`space-y-5 ${stickyPurchaseBar ? "pb-24 md:pb-0" : ""}`}
    >
      <div className="space-y-2">
        <div className="overflow-hidden rounded-[var(--radius-md)] bg-surface-muted">
          {gallery[activeImage] ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={gallery[activeImage]}
              alt=""
              className="aspect-[4/3] w-full object-cover"
            />
          ) : (
            <div className="aspect-[4/3] w-full">
              <MerchFallbackVisual
                productType={product.product_type}
                productName={product.name}
                eventTitle={eventTitle}
              />
            </div>
          )}
        </div>
        {gallery.length > 1 ? (
          <div className="flex gap-2 overflow-x-auto">
            {gallery.map((url, index) => (
              <button
                key={`${url}-${index}`}
                type="button"
                onClick={() => setActiveImage(index)}
                className={`h-14 w-14 shrink-0 overflow-hidden rounded-[var(--radius-sm)] border ${
                  index === activeImage
                    ? "border-foreground"
                    : "border-border"
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={url} alt="" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap gap-1.5">
          {locked ? (
            <Badge tone="dark" size="sm">
              {product.access_label || "Exclusive"}
            </Badge>
          ) : (
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
          {!locked ? (
            <Badge tone="outline" size="sm">
              Pickup at event
            </Badge>
          ) : null}
          {product.is_vault_exclusive ? (
            <Badge tone="accent" size="sm">
              Vault exclusive
            </Badge>
          ) : null}
          {product.requires_ticket ? (
            <Badge tone="accent" size="sm">
              Requires ticket
            </Badge>
          ) : null}
        </div>
        {product.is_sponsor_branded && !locked ? (
          <SponsorBrandedMark
            brandName={product.sponsor_brand_name}
            logoUrl={product.sponsor_logo_url}
            description={product.sponsor_description}
          />
        ) : null}
        <p className="text-xl font-extrabold text-foreground">
          {canPurchase && variant
            ? formatNgn(variant.effective_price)
            : formatNgn(product.base_price)}
        </p>
        {product.description || product.short_description ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
            {product.description || product.short_description}
          </p>
        ) : null}
        <MerchAccessLockPanel
          product={product}
          hostSlug={hostSlug}
          eventSlug={eventSlug}
          loginNext={`/events/${eventSlug}/merch/${product.id}`}
        />
        {!locked && product.size_chart ? (
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

      {canPurchase && product.variants.length > 0 ? (
        <label className="block space-y-1.5 text-sm">
          <span className="font-bold text-foreground">Variant</span>
          <select
            className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2"
            value={variantId}
            onChange={(e) => {
              const nextId = e.target.value;
              setVariantId(nextId);
              setQuantity(1);
              trackMerchVariantSelected({
                targetEventId: eventId,
                hostId: hostId ?? undefined,
                merchProductId: product.id,
                merchVariantId: nextId,
              });
            }}
          >
            {product.variants.map((v) => {
              const left = variantAvailable(v);
              return (
                <option key={v.id} value={v.id} disabled={left <= 0}>
                  {v.label}
                  {left <= 0 ? " — Sold out" : ` — ${formatNgn(v.effective_price)}`}
                </option>
              );
            })}
          </select>
        </label>
      ) : null}

      {canPurchase ? (
        <label className="block space-y-1.5 text-sm">
          <span className="font-bold text-foreground">Quantity</span>
          <select
            className="w-full rounded-[var(--radius-md)] border border-border bg-card px-3 py-2"
            value={quantity}
            disabled={soldOut || maxQty < 1}
            onChange={(e) => setQuantity(Number(e.target.value))}
          >
            {Array.from({ length: Math.max(1, maxQty) }, (_, i) => i + 1).map(
              (n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ),
            )}
          </select>
        </label>
      ) : null}

      {canPurchase ? (
        <div className="space-y-1 rounded-[var(--radius-md)] border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
          <p className="font-bold text-foreground">Pickup</p>
          <p>
            {product.pickup_location_label ||
              product.pickup_instructions ||
              "Pickup at the event — details after purchase."}
          </p>
          {product.pickup_time_window ? (
            <p>{product.pickup_time_window}</p>
          ) : null}
        </div>
      ) : null}

      <div className="space-y-1 text-sm text-muted-foreground">
        <p>
          Event:{" "}
          <Link
            href={`/events/${eventSlug}`}
            className="font-semibold text-foreground underline-offset-2 hover:underline"
          >
            {eventTitle}
          </Link>
        </p>
        {hostName ? (
          <p>
            Host:{" "}
            {hostSlug ? (
              <Link
                href={`/@${hostSlug}`}
                className="font-semibold text-foreground underline-offset-2 hover:underline"
              >
                {hostName}
              </Link>
            ) : (
              <span className="font-semibold text-foreground">{hostName}</span>
            )}
          </p>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        {canPurchase ? (
          soldOut ? (
            <Button variant="ghost" disabled>
              Sold out
            </Button>
          ) : (
            <>
              <Button type="button" onClick={addToCart}>
                Add to cart
              </Button>
              <Link href={gatedCheckoutHref}>
                <Button variant="secondary">Go to checkout</Button>
              </Link>
            </>
          )
        ) : null}
        {showFullPageLink ? (
          <Link href={`/events/${eventSlug}/merch/${product.id}`}>
            <Button variant="secondary">Open full page</Button>
          </Link>
        ) : null}
        {user ? (
          <Button variant="ghost" onClick={() => setReportOpen(true)}>
            Report
          </Button>
        ) : null}
      </div>

      {visibleReviews && visibleReviews.review_count > 0 ? (
        <section className="space-y-3 border-t border-border pt-4">
          <h2 className="text-sm font-extrabold text-foreground">
            Reviews · {visibleReviews.average_rating?.toFixed(1)} (
            {visibleReviews.review_count})
          </h2>
          <ul className="space-y-3">
            {visibleReviews.reviews.map((r) => (
              <li key={r.id} className="space-y-1">
                <p className="text-sm font-semibold text-foreground">
                  {r.author_display_name}{" "}
                  <Badge tone="neutral" size="sm">
                    Verified purchase
                  </Badge>
                </p>
                <p className="text-sm">{"★".repeat(r.rating)}</p>
                {r.body ? (
                  <p className="text-sm text-muted-foreground">{r.body}</p>
                ) : null}
                {r.host_reply ? (
                  <p className="text-sm text-foreground">Host: {r.host_reply}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {stickyPurchaseBar && canPurchase ? (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-background/95 p-3 backdrop-blur md:hidden">
          <div className="mx-auto flex max-w-lg flex-wrap items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-extrabold text-foreground">
                {product.name}
              </p>
              <p className="text-sm font-bold tabular-nums text-foreground">
                {variant
                  ? formatNgn(variant.effective_price)
                  : formatNgn(product.base_price)}
              </p>
            </div>
            {soldOut ? (
              <Button size="sm" variant="ghost" disabled>
                Sold out
              </Button>
            ) : (
              <Button size="sm" type="button" onClick={addToCart}>
                Add to cart
              </Button>
            )}
          </div>
        </div>
      ) : null}

      <ReportMerchDialog
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        onSubmit={async (reason, details) => {
          try {
            await reportMerchProduct(product.id, {
              reason,
              details: details || null,
            });
            toast.push({ tone: "success", title: "Report submitted" });
          } catch (err) {
            toast.push({
              tone: "danger",
              title: err instanceof ApiError ? err.detail : "Report failed",
            });
            throw err;
          }
        }}
      />
      <MerchSizeGuideModal
        open={sizeGuideOpen}
        onClose={() => setSizeGuideOpen(false)}
        chart={product.size_chart}
      />
    </div>
  );
}
