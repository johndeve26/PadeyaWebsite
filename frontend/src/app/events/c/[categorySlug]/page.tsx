import { CategoryLandingClient } from "@/components/discovery/CategoryLandingClient";
import {
  fetchTaxonomyCategoryBySlug,
  HubJsonLd,
  hubPageMetadata,
} from "@/lib/seo/hub-page";
import { taxonomyHeroAlt, taxonomyHeroFocal } from "@/lib/discovery/browse-images";
import { buildCategoryTrail } from "@/lib/marketplace-breadcrumbs";

type Props = { params: Promise<{ categorySlug: string }> };

export async function generateMetadata({ params }: Props) {
  const { categorySlug } = await params;
  const term = await fetchTaxonomyCategoryBySlug(categorySlug);
  const label = term?.name || categorySlug.replace(/-/g, " ");
  return hubPageMetadata({
    title: `${label} events`,
    description:
      term?.description ||
      `Browse ${label} events on Pàdéyá — filter by city, price, and format.`,
    path: `/events/c/${categorySlug}`,
    seoTitle: term?.seo_title,
    seoDescription: term?.seo_description,
  });
}

export default async function CategoryHubPage({ params }: Props) {
  const { categorySlug } = await params;
  const term = await fetchTaxonomyCategoryBySlug(categorySlug);
  const label = term?.name || categorySlug.replace(/-/g, " ");
  const description =
    term?.seo_description ||
    term?.description ||
    `Browse ${label} events on Pàdéyá — nights built around this interest.`;
  const crumbs = buildCategoryTrail(label, categorySlug);
  const heroFocal = taxonomyHeroFocal(term);

  return (
    <>
      <HubJsonLd
        name={`${label} events`}
        description={description}
        path={`/events/c/${categorySlug}`}
        crumbs={crumbs}
      />
      <CategoryLandingClient
        categorySlug={categorySlug}
        categoryName={label}
        categoryDescription={description}
        crumbs={crumbs}
        primaryImageUrl={term?.primary_image_url ?? term?.image_url ?? null}
        heroImageUrl={term?.hero_image_url ?? null}
        imageAlt={taxonomyHeroAlt(term, label)}
        focalX={heroFocal.focalX}
        focalY={heroFocal.focalY}
      />
    </>
  );
}
