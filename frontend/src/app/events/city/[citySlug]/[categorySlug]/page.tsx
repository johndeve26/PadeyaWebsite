import { CategoryLandingClient } from "@/components/discovery/CategoryLandingClient";
import { fetchPublicEventsServer } from "@/lib/events/public-server";
import { taxonomyHeroAlt, taxonomyHeroFocal } from "@/lib/discovery/browse-images";
import { buildCityCategoryTrail } from "@/lib/marketplace-breadcrumbs";
import {
  evaluateCityCategoryHubEligibility,
  locationHubFallbackCopy,
} from "@/lib/seo/hub-eligibility";
import {
  fetchTaxonomyCategoryBySlug,
  fetchTaxonomyLocationBySlug,
  HubJsonLd,
  hubPageMetadata,
} from "@/lib/seo/hub-page";

type Props = {
  params: Promise<{ citySlug: string; categorySlug: string }>;
};

export async function generateMetadata({ params }: Props) {
  const { citySlug, categorySlug } = await params;
  const [loc, term, events] = await Promise.all([
    fetchTaxonomyLocationBySlug(citySlug),
    fetchTaxonomyCategoryBySlug(categorySlug),
    fetchPublicEventsServer({
      location_kind: "city",
      location_slug: citySlug,
      category: categorySlug,
    }),
  ]);
  const city = loc?.name || citySlug.replace(/-/g, " ");
  const cat = term?.name || categorySlug.replace(/-/g, " ");
  const fallback = locationHubFallbackCopy({
    locationName: city,
    kind: "city",
    categoryName: cat,
  });
  const eligibility = evaluateCityCategoryHubEligibility({
    cityExists: Boolean(loc),
    cityActive: loc?.is_active,
    categoryExists: Boolean(term),
    categoryActive: term?.is_active !== false,
    eventCount: events.length,
    citySeoIndexMode: (loc as { seo_index_mode?: string } | null)?.seo_index_mode,
  });

  return hubPageMetadata({
    title: fallback.title,
    description:
      term?.seo_description ||
      fallback.description,
    path: `/events/city/${citySlug}/${categorySlug}`,
    seoTitle: term?.seo_title ? `${term.seo_title} · ${city}` : undefined,
    seoDescription: term?.seo_description,
    noIndex: !eligibility.indexable,
    noIndexFollow: true,
  });
}

export default async function CityCategoryHubPage({ params }: Props) {
  const { citySlug, categorySlug } = await params;
  const [loc, term] = await Promise.all([
    fetchTaxonomyLocationBySlug(citySlug),
    fetchTaxonomyCategoryBySlug(categorySlug),
  ]);
  const city = loc?.name || citySlug.replace(/-/g, " ");
  const cat = term?.name || categorySlug.replace(/-/g, " ");
  const description =
    term?.seo_description ||
    locationHubFallbackCopy({
      locationName: city,
      kind: "city",
      categoryName: cat,
    }).description;
  const path = `/events/city/${citySlug}/${categorySlug}`;
  const crumbs = buildCityCategoryTrail(city, citySlug, cat, categorySlug);
  const heroFocal = taxonomyHeroFocal(term);

  return (
    <>
      <HubJsonLd
        name={`${cat} events in ${city}`}
        description={description}
        path={path}
        crumbs={crumbs}
      />
      <CategoryLandingClient
        categorySlug={categorySlug}
        categoryName={cat}
        categoryDescription={description}
        crumbs={crumbs}
        citySlug={citySlug}
        cityName={city}
        primaryImageUrl={term?.primary_image_url ?? term?.image_url ?? null}
        heroImageUrl={term?.hero_image_url ?? null}
        imageAlt={taxonomyHeroAlt(term, cat)}
        focalX={heroFocal.focalX}
        focalY={heroFocal.focalY}
      />
    </>
  );
}
