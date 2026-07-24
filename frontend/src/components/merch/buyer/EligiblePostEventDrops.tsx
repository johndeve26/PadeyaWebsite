"use client";

import Link from "next/link";
import { useState } from "react";

import { MerchFallbackVisual } from "@/components/merch/MerchFallbackVisual";
import { Badge, Button } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import { productImageUrl } from "@/lib/merch-fallback";
import type { MerchCatalogProduct } from "@/lib/types/merch";

function dropHref(drop: MerchCatalogProduct): string {
  if (drop.event_slug) return `/events/${drop.event_slug}/merch`;
  return "/events";
}

function dropReason(drop: MerchCatalogProduct): string {
  if (drop.access_reason) return drop.access_reason;
  if (drop.access_label) return drop.access_label;
  if (drop.event_title) {
    return `Available because you attended ${drop.event_title}`;
  }
  return "Available from an eligible event you attended or bought.";
}

function DropCard({ drop }: { drop: MerchCatalogProduct }) {
  const image = productImageUrl(drop);
  const price = Number(drop.base_price);
  const href = dropHref(drop);

  return (
    <article className="flex h-full min-w-0 w-full flex-col overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)] dark:bg-surface-elevated">
      <div className="relative aspect-[16/10] w-full bg-muted sm:aspect-[5/3]">
        {image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={image} alt="" className="h-full w-full object-cover" />
        ) : (
          <MerchFallbackVisual
            productType={drop.product_type}
            productName={drop.name}
            eventTitle={drop.event_title}
            compact
          />
        )}
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="outline" size="sm">
            Post-event drop
          </Badge>
          {Number.isFinite(price) ? (
            <span className="text-sm font-bold text-foreground">
              {formatNgn(price)}
            </span>
          ) : null}
        </div>
        <h3 className="text-base font-extrabold tracking-tight text-heading sm:text-lg">
          {drop.name}
        </h3>
        {drop.event_title ? (
          <p className="text-sm text-muted-foreground">{drop.event_title}</p>
        ) : null}
        <p className="line-clamp-2 text-sm text-muted-foreground">
          {dropReason(drop)}
        </p>
        <div className="mt-auto pt-2">
          <Link href={href}>
            <Button size="sm" variant="secondary" className="w-full">
              View merch
            </Button>
          </Link>
        </div>
      </div>
    </article>
  );
}

export function EligiblePostEventDrops({
  drops,
}: {
  drops: MerchCatalogProduct[];
}) {
  const [showAll, setShowAll] = useState(false);
  if (!drops.length) return null;

  const visible = showAll ? drops : drops.slice(0, 4);
  const colClass =
    visible.length === 1
      ? "grid gap-4 grid-cols-1 md:max-w-xl"
      : visible.length === 2
        ? "grid gap-4 grid-cols-1 sm:grid-cols-2"
        : "grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4";

  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-lg font-extrabold tracking-tight text-heading">
          Eligible post-event drops
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Recap merch you can still buy because you attended or bought from
          eligible events.
        </p>
      </div>
      <div className={colClass}>
        {visible.map((drop) => (
          <DropCard key={drop.id} drop={drop} />
        ))}
      </div>
      {drops.length > 4 ? (
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setShowAll((v) => !v)}
        >
          {showAll ? "Show less" : "Show more"}
        </Button>
      ) : null}
    </section>
  );
}
