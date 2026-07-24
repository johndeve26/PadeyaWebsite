"use client";

import Link from "next/link";

import { Badge, Button, Media } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatNgn } from "@/lib/format";
import type { VaultLibraryItem } from "@/lib/types/vault";
import { formatAccessType, vaultCtaLabel } from "@/lib/vault-lock-copy";

type Props = {
  item: VaultLibraryItem;
  className?: string;
};

function itemHref(item: VaultLibraryItem): string {
  if (item.has_access) {
    return `/dashboard/vault/${item.id}`;
  }
  if (item.host_username && item.slug) {
    return `/@${item.host_username}/vault/${item.slug}`;
  }
  return `/dashboard/vault/${item.id}`;
}

export function BuyerVaultLibraryCard({ item, className = "" }: Props) {
  const href = itemHref(item);
  const locked = item.locked || !item.has_access;
  const priceLabel =
    item.access?.access_type === "one_time_unlock" && locked
      ? formatNgn(item.access?.price ?? item.price)
      : null;

  return (
    <article
      className={cn(
        "group flex h-full flex-col overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)] transition-[transform,box-shadow] duration-300 hover:-translate-y-0.5 hover:shadow-[var(--shadow)]",
        className,
      )}
    >
      <Link href={href} className="relative block aspect-[16/10] overflow-hidden bg-surface-dark">
        {item.cover_url ? (
          <Media
            src={item.cover_url}
            alt=""
            className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.04]"
          />
        ) : (
          <div className="padeya-hero-glow absolute inset-0" />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-ink/65 via-transparent to-ink/15" />
        <div className="absolute left-3 top-3 flex flex-wrap gap-2">
          <Badge tone="accent">{item.access_label}</Badge>
          <Badge tone="dark">
            {formatAccessType(item.access?.access_type)}
          </Badge>
        </div>
        <div className="absolute right-3 top-3">
          <Badge tone={locked ? "dark" : "success"}>
            {locked ? "Locked" : "Unlocked"}
          </Badge>
        </div>
      </Link>

      <div className="flex flex-1 flex-col gap-3 p-4 sm:p-5">
        <div className="space-y-1">
          {item.host_display_name || item.host_username ? (
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
              {item.host_display_name || `@${item.host_username}`}
            </p>
          ) : null}
          <h3 className="text-lg font-extrabold tracking-tight text-foreground">
            <Link href={href} className="hover:underline">
              {item.title}
            </Link>
          </h3>
          <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground">
            {item.preview_text ||
              "Exclusive Vault drop from a host you follow or support."}
          </p>
        </div>

        {item.related_event ? (
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground">
            Event · {item.related_event.title}
          </p>
        ) : null}

        {priceLabel ? (
          <p className="text-sm font-extrabold text-foreground">
            Unlock {priceLabel}
          </p>
        ) : null}

        <div className="mt-auto pt-1">
          <Link href={href}>
            <Button size="sm" className="w-full">
              {locked ? vaultCtaLabel(item) : "Open"}
            </Button>
          </Link>
        </div>
      </div>
    </article>
  );
}
