import Link from "next/link";

import { cn } from "@/lib/cn";

import { Badge } from "./Badge";
import { Card } from "./Card";
import { Media } from "./Media";

export function MemoryCard({
  title,
  href,
  dateLabel,
  city,
  rating,
  imageUrl,
  attendeesLabel,
  photosCount,
  videosCount,
  className = "",
}: {
  title: string;
  href: string;
  dateLabel: string;
  city?: string | null;
  rating?: number | null;
  imageUrl?: string | null;
  /** Optional — only render when real data is passed */
  attendeesLabel?: string | null;
  photosCount?: number | null;
  videosCount?: number | null;
  className?: string;
}) {
  const mediaBits = [
    photosCount != null && photosCount > 0 ? `${photosCount} photos` : null,
    videosCount != null && videosCount > 0 ? `${videosCount} videos` : null,
  ].filter(Boolean);

  return (
    <Link href={href} className={cn("group block h-full", className)}>
      <Card
        hover
        padded={false}
        className="flex h-full flex-col overflow-hidden transition-[transform,box-shadow] duration-200 group-hover:-translate-y-1 group-hover:shadow-[var(--shadow)]"
      >
        <div className="relative aspect-[4/3] overflow-hidden bg-surface-dark sm:aspect-[5/4]">
          {imageUrl ? (
            <Media
              src={imageUrl}
              alt=""
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.05]"
            />
          ) : (
            <div className="padeya-hero-glow absolute inset-0" />
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-ink/80 via-ink/20 to-transparent" />
          <div className="absolute left-3 top-3 flex flex-wrap gap-2">
            <Badge tone="accent">Memory</Badge>
            {rating != null ? (
              <Badge tone="dark">{Number(rating).toFixed(1)}★</Badge>
            ) : null}
          </div>
          <div className="absolute inset-x-0 bottom-0 space-y-1 p-4 sm:p-5">
            <h3 className="text-xl font-extrabold tracking-tight text-paper [text-shadow:0_2px_16px_rgb(0_0_0_/_0.45)] sm:text-2xl">
              {title}
            </h3>
            <p className="text-sm font-medium text-paper/80">
              {dateLabel}
              {city ? ` · ${city}` : ""}
            </p>
          </div>
        </div>
        <div className="flex flex-1 flex-col gap-2 px-5 py-4 sm:px-6 sm:py-5">
          {attendeesLabel || mediaBits.length > 0 ? (
            <p className="text-sm text-muted-foreground">
              {[attendeesLabel, ...mediaBits].filter(Boolean).join(" · ")}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              Recap from a completed Pàdéyá night
            </p>
          )}
          <p className="mt-auto pt-1 text-sm font-bold text-foreground transition-transform duration-200 group-hover:translate-x-0.5">
            Open Memory →
          </p>
        </div>
      </Card>
    </Link>
  );
}
