import {
  LocationHubPage,
  locationHubMetadata,
} from "@/lib/discovery/location-hub-page";
import { fetchTaxonomyCategoryBySlug } from "@/lib/seo/hub-page";

type Props = {
  params: Promise<{ stateSlug: string; categorySlug: string }>;
};

export async function generateMetadata({ params }: Props) {
  const { stateSlug, categorySlug } = await params;
  const cat = await fetchTaxonomyCategoryBySlug(categorySlug);
  return locationHubMetadata(
    "state",
    stateSlug,
    cat?.name || categorySlug,
  );
}

export default async function StateCategoryHubPage({ params }: Props) {
  const { stateSlug, categorySlug } = await params;
  const cat = await fetchTaxonomyCategoryBySlug(categorySlug);
  return (
    <LocationHubPage
      kind="state"
      slug={stateSlug}
      hubKind="state_category"
      categorySlug={categorySlug}
      categoryName={cat?.name || categorySlug}
    />
  );
}
