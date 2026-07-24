import { DiscoveryHubHero } from "@/components/discovery/DiscoveryHubHero";
import { brand } from "@/lib/brand";
import { cityBrowseImage } from "@/lib/discovery/browse-images";
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
}: {
  kind: string;
  slug: string;
  name: string;
  description?: string;
  className?: string;
}) {
  const basePath = locationHubPath(kind, slug);
  const heroImage =
    kind === "city" ? cityBrowseImage(slug) : brand.heroImage;

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
      className={className}
    />
  );
}
