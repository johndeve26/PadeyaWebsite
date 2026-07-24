import Link from "next/link";

import { cn } from "@/lib/cn";

import { Badge } from "./Badge";
import { Button } from "./Button";
import { Card } from "./Card";
import { Media } from "./Media";

export function VaultCard({
  title,
  description,
  href,
  imageUrl,
  priceLabel,
  locked,
  accessTypeLabel,
  relatedEventLabel,
  relatedEventHref,
  ctaLabel = "View",
  className = "",
}: {
  title: string;
  description?: string | null;
  href: string;
  imageUrl?: string | null;
  priceLabel?: string | null;
  locked?: boolean;
  accessTypeLabel?: string | null;
  relatedEventLabel?: string | null;
  relatedEventHref?: string | null;
  ctaLabel?: string | null;
  className?: string;
}) {
  return (
    <Card hover padded={false} className={cn("flex h-full flex-col overflow-hidden", className)}>
      <Link href={href} className="group block min-w-0 flex-1">
        <div className="relative aspect-[16/10] bg-surface-dark">
          {imageUrl ? (
            <Media
              src={imageUrl}
              className={cn(
                "transition-transform duration-500 group-hover:scale-[1.03]",
                locked && "brightness-50",
              )}
            />
          ) : (
            <div className="padeya-hero-glow absolute inset-0" />
          )}
          <div
            aria-hidden
            className="absolute inset-0 bg-gradient-to-t from-ink/55 via-transparent to-ink/15"
          />
          <div className="absolute left-3 top-3 flex flex-wrap gap-2">
            {accessTypeLabel ? <Badge tone="accent">{accessTypeLabel}</Badge> : null}
          </div>
          <div className="absolute right-3 top-3">
            <Badge tone={locked ? "warning" : "success"}>
              {locked ? "Locked" : "Unlocked"}
            </Badge>
          </div>
        </div>
        <div className="space-y-2 p-4 sm:p-5">
          <h3 className="text-base font-bold tracking-tight text-foreground sm:text-lg">
            {title}
          </h3>
          {description ? (
            <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground">
              {description}
            </p>
          ) : null}
          {relatedEventLabel ? (
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground">
              Event · {relatedEventLabel}
            </p>
          ) : null}
          {priceLabel ? (
            <p className="pt-1 text-sm font-bold text-foreground">{priceLabel}</p>
          ) : null}
        </div>
      </Link>
      <div className="flex flex-wrap gap-2 border-t border-border px-4 py-3 sm:px-5">
        <Link href={href} className="flex-1">
          <Button size="sm" className="w-full">
            {ctaLabel || "View"}
          </Button>
        </Link>
        {relatedEventHref ? (
          <Link href={relatedEventHref}>
            <Button size="sm" variant="ghost">
              Event
            </Button>
          </Link>
        ) : null}
      </div>
    </Card>
  );
}
