"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { MerchAccessLockPanel } from "@/components/merch/MerchAccessLockPanel";
import { MerchSizeGuideModal } from "@/components/merch/MerchSizeGuideModal";
import {
  Alert,
  Badge,
  Button,
  Container,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { trackMerchVaultExclusiveViewed } from "@/lib/analytics";
import {
  fetchHostMerchStorefrontProduct,
  fetchProductReviews,
} from "@/lib/merch-api";
import type { MerchCatalogProduct } from "@/lib/types/merch";

export default function HostMerchProductPage() {
  const params = useParams<{ username: string; productId: string }>();
  const username = decodeURIComponent(params.username).replace(/^@/, "");
  const productId = params.productId;
  const [product, setProduct] = useState<MerchCatalogProduct | null>(null);
  const [reviews, setReviews] = useState<{
    average_rating: number | null;
    review_count: number;
    reviews: Array<{
      id: string;
      rating: number;
      body?: string | null;
      author_display_name: string;
      verified_purchase?: boolean;
      event_title?: string | null;
      event_slug?: string | null;
      host_reply?: string | null;
    }>;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [sizeGuideOpen, setSizeGuideOpen] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const p = await fetchHostMerchStorefrontProduct(username, productId);
        if (!active) return;
        setProduct(p);
        setNotFound(false);
        setError(null);
        const vaultLocked = Boolean(
          (p.is_vault_exclusive || p.requires_vault_access) &&
            (p.access_locked || p.teaser_only || !p.access_eligible),
        );
        if (p.is_vault_exclusive || p.requires_vault_access) {
          trackMerchVaultExclusiveViewed({
            hostId: undefined,
            merchProductId: p.id,
            vaultLocked,
          });
        }
        if (!p.access_locked && !p.teaser_only && p.access_eligible !== false) {
          const r = await fetchProductReviews(productId).catch(() => null);
          if (active) setReviews(r);
        } else {
          setReviews(null);
        }
      } catch (err) {
        if (!active) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
          setError(null);
          setProduct(null);
          return;
        }
        setError(err instanceof ApiError ? err.detail : "Product unavailable");
      }
    })();
    return () => {
      active = false;
    };
  }, [username, productId]);

  if (notFound) {
    return (
      <Container className="py-16">
        <EmptyState
          title="Product not found"
          description="This merch item is not available on Pàdéyá."
        />
      </Container>
    );
  }

  if (error) {
    return (
      <Container className="py-16">
        <Alert tone="danger" title="Unavailable">
          {error}
        </Alert>
      </Container>
    );
  }

  if (!product) {
    return (
      <Container className="py-16">
        <SkeletonLoader lines={6} />
      </Container>
    );
  }

  const locked = Boolean(
    product.access_locked || product.teaser_only || !product.access_eligible,
  );
  const eligible = Boolean(product.access_eligible) && !locked;
  const eventHref =
    product.event_slug && !product.event_is_private
      ? `/events/${product.event_slug}`
      : null;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="relative min-h-[45vh] bg-surface-muted md:min-h-[55vh]">
        {product.cover_image_url || product.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={product.cover_image_url || product.image_url || ""}
            alt=""
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : null}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent" />
      </div>

      <Container className="relative -mt-20 space-y-8 pb-16 md:-mt-28">
        <div className="max-w-2xl space-y-4 rounded-none bg-background/95 p-6 backdrop-blur md:p-8">
          <Link
            href={`/@${username}/merch`}
            className="text-sm font-semibold text-muted-foreground hover:text-foreground"
          >
            ← Merch storefront
          </Link>
          <h1 className="font-display text-3xl font-black tracking-tight md:text-5xl">
            {product.name}
          </h1>
          {product.is_sponsor_branded ? (
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-3">
                {product.sponsor_logo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={product.sponsor_logo_url}
                    alt={
                      product.sponsor_brand_name
                        ? `${product.sponsor_brand_name} logo`
                        : "Sponsor logo"
                    }
                    className="h-8 w-auto max-w-[140px] object-contain"
                  />
                ) : null}
                <p className="text-sm text-muted-foreground">
                  Sponsor-branded
                  {product.sponsor_brand_name ? (
                    <>
                      {" "}
                      · In partnership with{" "}
                      <span className="font-semibold text-foreground">
                        {product.sponsor_brand_name}
                      </span>
                    </>
                  ) : null}
                </p>
              </div>
              {product.sponsor_description ? (
                <p className="text-sm text-muted-foreground">
                  {product.sponsor_description}
                </p>
              ) : null}
            </div>
          ) : null}
          {locked ? (
            <Badge tone="dark">{product.access_label || "Exclusive"}</Badge>
          ) : null}
          {product.availability === "coming_soon" ? (
            <Badge tone="neutral">Drop coming soon</Badge>
          ) : null}
          <p className="text-xl font-extrabold">
            ₦{Number(product.base_price).toLocaleString()}
          </p>
          {product.description || product.short_description ? (
            <p className="text-muted-foreground">
              {product.description || product.short_description}
            </p>
          ) : null}

          <MerchAccessLockPanel
            product={product}
            hostSlug={username}
            eventSlug={product.event_slug}
            loginNext={`/@${username}/merch/${product.id}`}
          />

          <div className="flex flex-wrap gap-2 pt-2">
            {eligible && eventHref ? (
              <Link href={eventHref}>
                <Button>Get it with the event</Button>
              </Link>
            ) : eligible ? (
              <Link href={`/@${username}/merch`}>
                <Button>Back to storefront</Button>
              </Link>
            ) : null}
            {eligible && product.size_chart ? (
              <Button
                variant="secondary"
                onClick={() => setSizeGuideOpen(true)}
              >
                Size guide
              </Button>
            ) : null}
            <Link
              href={`/@${username}`}
              className="inline-flex items-center text-sm font-semibold text-foreground underline-offset-4 hover:underline"
            >
              Legacy page
            </Link>
          </div>

          <MerchSizeGuideModal
            open={sizeGuideOpen}
            onClose={() => setSizeGuideOpen(false)}
            chart={product.size_chart}
          />
        </div>

        {!locked && reviews ? (
          <section className="max-w-2xl space-y-4">
            <h2 className="text-lg font-extrabold">
              Reviews
              {reviews.review_count > 0
                ? ` · ${reviews.average_rating?.toFixed(1)} (${reviews.review_count})`
                : " · none yet"}
            </h2>
            {reviews.review_count === 0 ? (
              <p className="text-sm text-muted-foreground">
                Verified buyers can leave a review after purchase.
              </p>
            ) : (
              <ul className="space-y-4">
                {reviews.reviews.map((r) => (
                  <li key={r.id} className="border-t border-border pt-4">
                    <p className="text-sm font-semibold">
                      {r.author_display_name}{" "}
                      <Badge tone="neutral" size="sm">
                        Verified purchase
                      </Badge>
                    </p>
                    <p className="text-sm">{"★".repeat(r.rating)}</p>
                    {r.body ? (
                      <p className="mt-1 text-sm text-muted-foreground">
                        {r.body}
                      </p>
                    ) : null}
                    {r.event_title && r.event_slug ? (
                      <p className="mt-2 text-xs text-muted-foreground">
                        From{" "}
                        <Link
                          href={`/events/${r.event_slug}`}
                          className="font-semibold text-foreground underline-offset-4 hover:underline"
                        >
                          {r.event_title}
                        </Link>
                      </p>
                    ) : r.event_title ? (
                      <p className="mt-2 text-xs text-muted-foreground">
                        From {r.event_title}
                      </p>
                    ) : null}
                    {r.host_reply ? (
                      <p className="mt-2 text-sm text-foreground">
                        Host: {r.host_reply}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
        ) : null}
      </Container>
    </div>
  );
}
