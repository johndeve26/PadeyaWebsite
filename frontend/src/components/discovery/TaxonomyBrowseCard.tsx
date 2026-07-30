import Link from "next/link";

import { Media } from "@/components/ui";
import { cn } from "@/lib/cn";

/**
 * Image-led taxonomy shortcut card (city / interest / collection)
 * for dedicated landing rails and “Keep exploring” grids.
 */
export function TaxonomyBrowseCard({
  href,
  title,
  meta,
  image,
  imageAlt,
  focalX = 0.5,
  focalY = 0.5,
  eyebrow,
  className = "",
}: {
  href: string;
  title: string;
  meta: string;
  image: string;
  imageAlt?: string;
  focalX?: number;
  focalY?: number;
  /** Optional type line (Category, City, Hosts…). */
  eyebrow?: string;
  className?: string;
}) {
  const alt = imageAlt?.trim() || title;
  const objectPosition = `${Math.round(Math.min(1, Math.max(0, focalX)) * 100)}% ${Math.round(Math.min(1, Math.max(0, focalY)) * 100)}%`;

  return (
    <Link
      href={href}
      className={cn(
        "padeya-discovery-card group relative flex h-full flex-col overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card",
        "transition-[border-color,box-shadow] duration-300 hover:border-border-strong/30 hover:shadow-[var(--shadow)]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background",
        className,
      )}
    >
      <div className="relative aspect-[16/11] overflow-hidden bg-ink">
        <Media
          src={image}
          alt={alt}
          className="padeya-image-zoom absolute inset-0 h-full w-full object-cover"
          style={{ objectPosition }}
        />
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-t from-ink/85 via-ink/25 to-transparent"
        />
        <div className="absolute inset-x-0 bottom-0 space-y-0.5 p-4 sm:p-5">
          {eyebrow ? (
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-accent">
              {eyebrow}
            </p>
          ) : null}
          {/* Title once in overlay — do not duplicate behind media */}
          <p className="text-base font-extrabold tracking-tight text-paper sm:text-lg">
            {title}
          </p>
        </div>
      </div>
      <div className="flex flex-1 flex-col justify-between gap-2 p-4 sm:p-5">
        <p className="text-sm leading-relaxed text-muted-foreground">{meta}</p>
        <span className="text-sm font-bold uppercase tracking-[0.08em] text-foreground/55 transition-colors group-hover:text-foreground">
          Browse →
        </span>
      </div>
    </Link>
  );
}
