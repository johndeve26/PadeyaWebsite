"use client";

import Link from "next/link";

import { TrackImpression } from "@/components/analytics/TrackImpression";
import { Badge, Button, Media } from "@/components/ui";
import {
  trackVaultItemClick,
  trackVaultItemImpression,
} from "@/lib/analytics";
import { cn } from "@/lib/cn";
import { formatNgn } from "@/lib/format";
import type { VaultCatalogCard } from "@/lib/types/vault";
import { formatAccessType, vaultCtaLabel } from "@/lib/vault-lock-copy";

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

type Props = {
  item: VaultCatalogCard;
  username: string;
  featured?: boolean;
  className?: string;
  hostId?: string | null;
  sourcePage?: string;
  listContext?: string;
  cardPosition?: number;
};

export function PublicVaultItemCard({
  item,
  username,
  featured = false,
  className = "",
  hostId = null,
  sourcePage = "vault_catalog",
  listContext = "vault_catalog",
  cardPosition,
}: Props) {
  const href = item.share_path || `/@${username}/vault/${item.slug}`;
  const cta = vaultCtaLabel(item);
  const isFeatured = featured || Boolean(item.featured);
  const priceLabel =
    item.access_type === "one_time_unlock" && item.price != null
      ? item.locked
        ? `Unlock ${formatNgn(item.price)}`
        : formatNgn(item.price)
      : null;

  function onClickTrack() {
    if (!hostId) return;
    trackVaultItemClick({
      hostId,
      vaultItemId: item.id,
      accessType: item.access_type,
      relatedEventId: item.related_event?.id ?? null,
      lockedState: item.locked,
      sourcePage,
      listContext,
      cardPosition,
    });
  }

  const isLocked = item.locked || item.expired;

  const card = (
    <article
      className={cn(
        "group overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)] transition-[transform,box-shadow] duration-300 hover:-translate-y-0.5 hover:shadow-[var(--shadow)]",
        "dark:border-border dark:bg-surface-elevated dark:shadow-[var(--shadow)]",
        isFeatured
          ? "grid lg:grid-cols-2 lg:items-stretch"
          : "flex h-full flex-col",
        className,
      )}
    >
      <Link
        href={href}
        onClick={onClickTrack}
        className={cn(
          "relative block overflow-hidden bg-surface-dark",
          isFeatured
            ? "aspect-[16/10] lg:aspect-auto lg:min-h-[280px]"
            : "aspect-[16/10]",
        )}
      >
        {item.cover_url ? (
          <Media
            src={item.cover_url}
            alt=""
            className={cn(
              "h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.04]",
              isLocked && "scale-105 blur-sm brightness-50",
            )}
          />
        ) : (
          <div className="padeya-hero-glow absolute inset-0" />
        )}
        <div
          className={cn(
            "absolute inset-0 bg-gradient-to-t from-ink/70 via-transparent to-ink/20",
            isLocked && "from-ink/90 via-ink/45 to-ink/50",
          )}
        />
        {isLocked ? (
          <div
            aria-hidden
            className="absolute inset-0 flex items-center justify-center"
          >
            <span className="rounded-full border border-paper/25 bg-ink/55 px-3 py-1.5 text-xs font-extrabold uppercase tracking-[0.14em] text-paper backdrop-blur-sm">
              {item.expired ? "Expired" : "Locked"}
            </span>
          </div>
        ) : null}
        <div className="absolute left-3 top-3 flex flex-wrap gap-2">
          <Badge tone="accent">{formatAccessType(item.access_type)}</Badge>
          <Badge tone="dark">{formatLabel(item.content_type || "exclusive")}</Badge>
          {isFeatured ? <Badge tone="accent">Featured</Badge> : null}
        </div>
        <div className="absolute right-3 top-3">
          <Badge tone={item.expired ? "warning" : item.locked ? "warning" : "success"}>
            {item.expired ? "Expired" : item.locked ? "Locked" : "Unlocked"}
          </Badge>
        </div>
      </Link>

      <div className="flex flex-1 flex-col gap-3 p-4 sm:p-5 lg:justify-center lg:p-8">
        <div className="space-y-1.5">
          <h3
            className={cn(
              "font-extrabold tracking-tight text-foreground",
              isFeatured ? "text-2xl sm:text-3xl" : "text-lg",
            )}
          >
            <Link href={href} onClick={onClickTrack} className="hover:underline">
              {item.title}
            </Link>
          </h3>
          <p
            className={cn(
              "leading-relaxed text-muted-foreground",
              isFeatured ? "text-base" : "line-clamp-2 text-sm",
            )}
          >
            {item.preview_text ||
              "Exclusive host drop — preview freely, unlock for full access."}
          </p>
        </div>

        {item.related_event ? (
          <Link
            href={item.related_event.href}
            className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
          >
            Event · {item.related_event.title}
          </Link>
        ) : null}

        {priceLabel ? (
          <p className="text-sm font-extrabold text-foreground">{priceLabel}</p>
        ) : null}

        <div className="mt-auto flex flex-wrap gap-2 pt-1 lg:mt-4">
          <Link
            href={href}
            onClick={onClickTrack}
            className="min-w-[7rem] flex-1 sm:flex-none"
          >
            <Button size={isFeatured ? "lg" : "sm"} className="w-full sm:w-auto">
              {cta}
            </Button>
          </Link>
          {item.related_event?.href ? (
            <Link href={item.related_event.href}>
              <Button size={isFeatured ? "lg" : "sm"} variant="ghost">
                Related event
              </Button>
            </Link>
          ) : null}
        </div>
      </div>
    </article>
  );

  if (!hostId) return card;

  return (
    <TrackImpression
      as="div"
      targetEventId={item.id}
      hostId={hostId}
      listContext={listContext}
      cardPosition={cardPosition}
      trackCardImpression={false}
      onImpression={() => {
        trackVaultItemImpression({
          hostId,
          vaultItemId: item.id,
          accessType: item.access_type,
          relatedEventId: item.related_event?.id ?? null,
          lockedState: item.locked,
          sourcePage,
          listContext,
          cardPosition,
        });
      }}
    >
      {card}
    </TrackImpression>
  );
}
