import { CategoryLandingClient } from "@/components/discovery/CategoryLandingClient";
import { buildCityCategoryTrail } from "@/lib/marketplace-breadcrumbs";
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
  const [loc, term] = await Promise.all([
    fetchTaxonomyLocationBySlug(citySlug),
    fetchTaxonomyCategoryBySlug(categorySlug),
  ]);
  const city = loc?.name || citySlug.replace(/-/g, " ");
  const cat = term?.name || categorySlug.replace(/-/g, " ");
  return hubPageMetadata({
    title: `${cat} in ${city}`,
    description:
      term?.seo_description ||
      `${cat} events in ${city} on Pàdéyá — a focused city × interest landing.`,
    path: `/events/city/${citySlug}/${categorySlug}`,
    seoTitle: term?.seo_title
      ? `${term.seo_title} · ${city}`
      : undefined,
    seoDescription: term?.seo_description,
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
    term?.description ||
    `${cat} events in ${city} on Pàdéyá — a focused city × interest landing.`;
  const crumbs = buildCityCategoryTrail(city, citySlug, cat, categorySlug);

  return (
    <>
      <HubJsonLd
        name={`${cat} in ${city}`}
        description={description}
        path={`/events/city/${citySlug}/${categorySlug}`}
        crumbs={crumbs}
      />
      <CategoryLandingClient
        categorySlug={categorySlug}
        categoryName={cat}
        categoryDescription={description}
        crumbs={crumbs}
        citySlug={citySlug}
        cityName={city}
      />
    </>
  );
}
