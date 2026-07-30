import { DiscoveryHubHero } from "@/components/discovery/DiscoveryHubHero";
import { brand } from "@/lib/brand";
import { taxonomyHeroImage } from "@/lib/discovery/browse-images";
import { locationLandingSubtext } from "@/lib/discovery/location-landing";
import { locationHubPath } from "@/lib/taxonomy-api";

function eyebrowForKind(kind: string): string {
  if (kind === "city") return "City";
  if (kind === "area") return "Area";
  if (kind === "state") return "State";
  if (kind === "country") return "Country";
  return "Location";
}

/**
 * Full-bleed hero for country / state / city / area landing pages.
 */
export function LocationLandingHero({
  kind,
  slug,
  name,
  description,
  className = "",
  heroImageUrl,
  primaryImageUrl,
  imageAlt,
  focalX = 0.5,
  focalY = 0.5,
}: {
  kind: string;
  slug: string;
  name: string;
  description?: string;
  className?: string;
  heroImageUrl?: string | null;
  primaryImageUrl?: string | null;
  imageAlt?: string | null;
  focalX?: number;
  focalY?: number;
}) {
  const basePath = locationHubPath(kind, slug);
  const heroImage =
    kind === "city"
      ? taxonomyHeroImage(slug, "city", {
          heroUrl: heroImageUrl,
          primaryUrl: primaryImageUrl,
        })
      : heroImageUrl || primaryImageUrl || brand.heroImage;

  return (
    <DiscoveryHubHero
      eyebrow={eyebrowForKind(kind)}
      title={`What’s on in ${name}.`}
      description={description || locationLandingSubtext(name, { kind })}
      ctaLabel="Explore this weekend"
      ctaHref={`${basePath}?weekend=1#events`}
      secondaryCtaLabel={`All ${name} events`}
      secondaryCtaHref={`${basePath}#events`}
      backgroundSrc={heroImage}
      backgroundAlt={imageAlt?.trim() || name}
      backgroundFocalX={focalX}
      backgroundFocalY={focalY}
      className={className}
    />
  );
}
