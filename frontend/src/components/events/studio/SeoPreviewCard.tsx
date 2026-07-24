"use client";

import { Card, Media } from "@/components/ui";

import { STUDIO_MEDIA_PLACEHOLDERS } from "./studio-media-placeholders";

/** Live search + social previews for Event Studio — public-safe location only. */
export function SeoPreviewCard({
  title,
  description,
  path,
  locationLabel,
  socialTitle,
  socialDescription,
  imageUrl,
}: {
  title: string;
  description: string;
  path: string;
  locationLabel?: string;
  socialTitle?: string;
  socialDescription?: string;
  imageUrl?: string | null;
}) {
  const shareTitle = socialTitle || title || "Event title";
  const shareDescription =
    socialDescription ||
    description ||
    "Add a short description for search and social.";
  const image = imageUrl?.trim() || STUDIO_MEDIA_PLACEHOLDERS.social;

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="space-y-3 padeya-stat-surface shadow-[var(--shadow-soft)]">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
            Search preview
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Approximate Google-style snippet — keep it public-safe.
          </p>
        </div>
        <div className="rounded-[var(--radius-md)] border border-border bg-paper px-3 py-3 text-ink">
          <p className="text-base font-semibold text-[#1a0dab] line-clamp-1">
            {title || "Event title"} · Pàdéyá
          </p>
          <p className="mt-0.5 text-xs text-[#006621] break-all">
            {path || "https://padeya.com/events/…"}
          </p>
          <p className="mt-1 text-sm leading-relaxed text-[#4d5156] line-clamp-3">
            {description || "Add a short description for search and social."}
            {locationLabel ? ` · ${locationLabel}` : ""}
          </p>
        </div>
      </Card>

      <Card padded={false} className="overflow-hidden shadow-[var(--shadow-soft)]">
        <div className="space-y-0">
          <div className="px-4 pt-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
              Social preview
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              How your link can look when shared.
            </p>
          </div>
          <div className="relative mt-3 aspect-[1.91/1] bg-surface-dark">
            <Media src={image} alt="" className="object-cover" />
          </div>
          <div className="space-y-1 p-4">
            <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
              padeya.com
            </p>
            <p className="text-sm font-bold text-foreground line-clamp-2">
              {shareTitle} · Pàdéyá
            </p>
            <p className="text-xs leading-relaxed text-muted-foreground line-clamp-2">
              {shareDescription}
              {locationLabel ? ` · ${locationLabel}` : ""}
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}

export function TaxonomyFieldsHint({
  categoryRequired,
}: {
  categoryRequired?: boolean;
}) {
  return (
    <p className="text-sm text-muted-foreground">
      {categoryRequired
        ? "Primary category is required before submitting a listed public event."
        : "Add category, city, tags, and vibe so discovery hubs and related rails stay connected."}
    </p>
  );
}

/** Alias matching the product name in Studio specs. */
export { SeoPreviewCard as SEOPreviewCard };
