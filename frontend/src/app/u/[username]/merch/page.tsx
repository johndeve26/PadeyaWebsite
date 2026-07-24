"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  Alert,
  Badge,
  Container,
  EmptyState,
  Select,
  SkeletonCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import {
  fetchHostMerchStorefront,
  type HostMerchStorefront,
} from "@/lib/merch-api";
import { MERCH_PRODUCT_TYPES } from "@/lib/merch-product-types";
import type { MerchCatalogProduct } from "@/lib/types/merch";

const PRODUCT_TYPE_LABELS = Object.fromEntries(
  MERCH_PRODUCT_TYPES.map((t) => [t.value, t.label]),
) as Record<string, string>;

function productKindLabel(product: MerchCatalogProduct): string | null {
  if (product.is_vault_exclusive) return "Vault exclusive";
  if (product.is_post_event_drop) return "Post-event drop";
  if (product.is_sponsor_branded) return "Sponsor-branded";
  if (product.is_merch_only || !product.is_event_linked) return "Merch only";
  if (product.event_title) return "Event merch";
  return null;
}

function StorefrontProductCard({
  product,
  username,
}: {
  product: MerchCatalogProduct;
  username: string;
}) {
  const locked = Boolean(product.access_locked || product.teaser_only);
  const sponsor = Boolean(product.is_sponsor_branded);
  const kind = productKindLabel(product);
  const href = `/@${username}/merch/${product.id}`;

  return (
    <Link
      href={href}
      className={cn(
        "group block space-y-3 transition-transform duration-300 hover:-translate-y-0.5",
      )}
    >
      <div className="relative aspect-[4/5] overflow-hidden bg-surface-muted">
        {product.image_url || product.cover_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={product.cover_image_url || product.image_url || ""}
            alt=""
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
          />
        ) : (
          <span className="flex h-full items-center justify-center text-sm font-bold text-muted-foreground">
            Merch
          </span>
        )}
        <div className="absolute inset-x-0 bottom-0 space-y-1 bg-gradient-to-t from-black/75 to-transparent p-3">
          {locked ? (
            <Badge tone="dark" size="sm">
              {product.access_label || "Exclusive"}
            </Badge>
          ) : null}
          {!locked && product.availability === "coming_soon" ? (
            <Badge tone="dark" size="sm">
              Coming soon
            </Badge>
          ) : null}
          {kind ? (
            <p className="text-[11px] font-semibold uppercase tracking-wide text-white/85">
              {kind}
            </p>
          ) : null}
        </div>
      </div>
      <div className="space-y-1">
        <h3 className="text-base font-extrabold tracking-tight text-foreground">
          {product.name}
        </h3>
        {sponsor ? (
          <div className="flex items-center gap-2">
            {product.sponsor_logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={product.sponsor_logo_url}
                alt=""
                className="h-5 w-auto max-w-[72px] object-contain"
              />
            ) : null}
            {product.sponsor_brand_name ? (
              <p className="text-xs text-muted-foreground">
                In partnership with {product.sponsor_brand_name}
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">Sponsor-branded</p>
            )}
          </div>
        ) : null}
        {product.event_title && !product.event_is_private ? (
          <p className="text-xs text-muted-foreground">{product.event_title}</p>
        ) : null}
        <p className="text-sm font-semibold text-foreground">
          ₦{Number(product.base_price).toLocaleString()}
        </p>
      </div>
    </Link>
  );
}

export default function HostMerchStorefrontPage() {
  const params = useParams<{ username: string }>();
  const username = decodeURIComponent(params.username).replace(/^@/, "");
  const [data, setData] = useState<HostMerchStorefront | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [eventFilter, setEventFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [availabilityFilter, setAvailabilityFilter] = useState("");
  const [kindFilter, setKindFilter] = useState("");

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const row = await fetchHostMerchStorefront(username, {
          event: eventFilter || undefined,
          product_type: typeFilter || undefined,
          availability: availabilityFilter || undefined,
          kind: kindFilter || undefined,
        });
        if (!active) return;
        setData(row);
        setError(null);
        setNotFound(false);
      } catch (err) {
        if (!active) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
          setError(null);
          setData(null);
          return;
        }
        setError(
          err instanceof ApiError ? err.detail : "Storefront unavailable",
        );
      }
    })();
    return () => {
      active = false;
    };
  }, [username, eventFilter, typeFilter, availabilityFilter, kindFilter]);

  const eventOptions = useMemo(
    () => data?.filters?.events ?? [],
    [data?.filters?.events],
  );
  const typeOptions = useMemo(
    () => data?.filters?.product_types ?? [],
    [data?.filters?.product_types],
  );

  if (notFound) {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <Container className="py-24">
          <EmptyState
            title="Storefront not found"
            description="This merch shop is not available on Pàdéyá."
          />
        </Container>
      </div>
    );
  }

  const displayName = data?.host_name || username;
  const title = data?.storefront_title || displayName;
  const description =
    data?.storefront_description ||
    "Event merch from this host on Pàdéyá — pickup, drops, and exclusives.";
  const legacyHref = data?.legacy_path || `/@${username}`;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <section className="relative overflow-hidden border-b border-border bg-gradient-to-br from-[var(--surface)] via-background to-[var(--surface-muted)]">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-16 top-0 h-64 w-64 rounded-full bg-[var(--brand-gold)]/10 blur-3xl"
        />
        <Container className="relative py-16 md:py-24">
          <div className="flex flex-wrap items-end gap-6">
            {data?.host_avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={data.host_avatar_url}
                alt=""
                className="h-20 w-20 object-cover md:h-24 md:w-24"
              />
            ) : (
              <div className="flex h-20 w-20 items-center justify-center bg-surface-muted text-xl font-black text-muted-foreground md:h-24 md:w-24">
                {displayName.slice(0, 1).toUpperCase()}
              </div>
            )}
            <div className="min-w-0 flex-1 space-y-3">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
                Pàdéyá merch
              </p>
              <h1 className="max-w-2xl font-display text-4xl font-black tracking-tight text-foreground md:text-6xl">
                {title}
              </h1>
              <p className="max-w-xl text-base text-muted-foreground md:text-lg">
                {description}
              </p>
              <div className="flex flex-wrap items-center gap-3 pt-1">
                <p className="text-sm font-semibold text-foreground">
                  {displayName}
                </p>
                <Link
                  href={legacyHref}
                  className="text-sm font-semibold text-foreground underline-offset-4 hover:underline"
                >
                  Legacy page
                </Link>
                {data?.is_preview ? (
                  <Badge tone="neutral" size="sm">
                    Preview — not public
                  </Badge>
                ) : null}
              </div>
            </div>
          </div>
        </Container>
      </section>

      <Container className="py-12 md:py-16">
        {error ? (
          <Alert tone="danger" title="Could not load merch">
            {error}
          </Alert>
        ) : null}

        {!data && !error ? (
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : null}

        {data ? (
          <div className="space-y-8">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Select
                label="Event"
                value={eventFilter}
                onChange={(e) => setEventFilter(e.target.value)}
              >
                <option value="">All events</option>
                <option value="merch-only">Merch only</option>
                {eventOptions.map((ev) => (
                  <option
                    key={String(ev.event_slug || ev.event_id)}
                    value={String(ev.event_slug || ev.event_id)}
                  >
                    {ev.event_title || ev.event_slug}
                  </option>
                ))}
              </Select>
              <Select
                label="Kind"
                value={kindFilter}
                onChange={(e) => setKindFilter(e.target.value)}
              >
                <option value="">All kinds</option>
                <option value="host_storefront">Storefront</option>
                <option value="post_event_drop">Post-event</option>
                <option value="vault_exclusive">Vault exclusive</option>
              </Select>
              <Select
                label="Product type"
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
              >
                <option value="">All types</option>
                {typeOptions.map((type) => (
                  <option key={type} value={type}>
                    {PRODUCT_TYPE_LABELS[type] || type}
                  </option>
                ))}
              </Select>
              <Select
                label="Availability"
                value={availabilityFilter}
                onChange={(e) => setAvailabilityFilter(e.target.value)}
              >
                <option value="">All</option>
                <option value="purchasable">Purchasable</option>
                <option value="coming_soon">Coming soon</option>
                <option value="locked">Locked / exclusive</option>
                <option value="sold_out">Sold out</option>
              </Select>
            </div>

            {data.products.length === 0 ? (
              <EmptyState
                title="No merch yet"
                description="This host has not published storefront merch on Pàdéyá."
              />
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  {data.product_count} item
                  {data.product_count === 1 ? "" : "s"}
                </p>
                <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
                  {data.products.map((p) => (
                    <StorefrontProductCard
                      key={p.id}
                      product={p}
                      username={data.host_slug || username}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </Container>
    </div>
  );
}
