import { DiscoveryHubHero } from "@/components/discovery/DiscoveryHubHero";
import { taxonomyHeroImage } from "@/lib/discovery/browse-images";
import { categoryStory } from "@/lib/discovery/category-stories";
import { locationHubPath } from "@/lib/taxonomy-api";

/**
 * Full-bleed hero for interest / category landing pages.
 */
export function CategoryLandingHero({
  slug,
  name,
  description,
  cityName,
  citySlug,
  locationName,
  locationKind,
  locationSlug,
  className = "",
  heroImageUrl,
  primaryImageUrl,
  imageAlt,
  focalX = 0.5,
  focalY = 0.5,
}: {
  slug: string;
  name: string;
  description?: string;
  cityName?: string;
  citySlug?: string;
  locationName?: string;
  locationKind?: string;
  locationSlug?: string;
  className?: string;
  heroImageUrl?: string | null;
  primaryImageUrl?: string | null;
  imageAlt?: string | null;
  focalX?: number;
  focalY?: number;
}) {
  const placeName = cityName || locationName;
  const story = categoryStory(slug, name, description);
  const title = placeName
    ? `${name} in ${placeName}.`
    : `${name} worth showing up for.`;
  const body =
    description ||
    (placeName
      ? `${story.story} Browse verified ${name.toLowerCase()} nights in ${placeName}.`
      : story.story);

  const secondaryHref = citySlug
    ? locationHubPath("city", citySlug)
    : locationKind && locationSlug
      ? locationHubPath(locationKind, locationSlug)
      : "/events";

  return (
    <DiscoveryHubHero
      eyebrow={placeName ? `${placeName} · Interest` : "Interest"}
      title={title}
      description={body}
      ctaLabel="See what’s on"
      ctaHref="#events"
      secondaryCtaLabel={placeName ? `All ${placeName} events` : "All events"}
      secondaryCtaHref={secondaryHref}
      backgroundSrc={taxonomyHeroImage(slug, "category", {
        heroUrl: heroImageUrl,
        primaryUrl: primaryImageUrl,
      })}
      backgroundAlt={imageAlt?.trim() || name}
      backgroundFocalX={focalX}
      backgroundFocalY={focalY}
      className={className}
    />
  );
}
