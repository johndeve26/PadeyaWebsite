import Link from "next/link";

import { TaxonomyBrowseCard } from "@/components/discovery/TaxonomyBrowseCard";
import { Container } from "@/components/ui";
import { cn } from "@/lib/cn";
import { cityBrowseImage } from "@/lib/discovery/browse-images";
import { brand } from "@/lib/brand";
import { locationHubPath } from "@/lib/taxonomy-api";

export type RelatedLocationItem = {
  kind: string;
  slug: string;
  name: string;
  imageUrl?: string | null;
  imageAlt?: string | null;
  focalX?: number | null;
  focalY?: number | null;
};

function locationBrowseImage(
  kind: string,
  slug: string,
  imageUrl?: string | null,
): string {
  if (kind === "city") return cityBrowseImage(slug, imageUrl);
  return brand.heroImage;
}

/**
 * Related / nearby location cards for location landing pages.
 */
export function RelatedLocations({
  locations,
  title = "Explore nearby and similar places",
  eyebrow = "Related locations",
  footerHref = "/events/location",
  footerLabel = "Browse all locations →",
  className = "",
}: {
  locations: RelatedLocationItem[];
  title?: string;
  eyebrow?: string;
  footerHref?: string;
  footerLabel?: string;
  className?: string;
}) {
  if (!locations.length) return null;

  return (
    <section
      aria-label="Related locations"
      className={cn("bg-muted py-12 sm:py-14", className)}
    >
      <Container className="space-y-7">
        <div className="max-w-2xl space-y-2">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
            {eyebrow}
          </p>
          <h2 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
            {title}
          </h2>
        </div>
        <ul className="grid auto-rows-fr gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 xl:grid-cols-4">
          {locations.slice(0, 8).map((loc) => (
            <li key={`${loc.kind}:${loc.slug}`} className="h-full">
              <TaxonomyBrowseCard
                href={locationHubPath(loc.kind, loc.slug)}
                title={loc.name}
                meta={loc.kind.replace(/_/g, " ")}
                image={locationBrowseImage(loc.kind, loc.slug, loc.imageUrl)}
                imageAlt={loc.imageAlt || loc.name}
                focalX={loc.focalX ?? 0.5}
                focalY={loc.focalY ?? 0.5}
                className="h-full"
              />
            </li>
          ))}
        </ul>
        <div>
          <Link
            href={footerHref}
            className="text-sm font-bold text-foreground underline-offset-4 hover:underline"
          >
            {footerLabel}
          </Link>
        </div>
      </Container>
    </section>
  );
}
