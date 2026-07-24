import { CategoryLandingClient } from "@/components/discovery/CategoryLandingClient";
import { DiscoveryHubClient } from "@/components/discovery/DiscoveryHubClient";
import { LocationLandingClient } from "@/components/discovery/LocationLandingClient";
import type { HubKind } from "@/lib/discovery/hub-kind";
import { locationLandingSubtext } from "@/lib/discovery/location-landing";
import { buildLocationTrail } from "@/lib/marketplace-breadcrumbs";
import {
  fetchTaxonomyLocationDetailSeo,
  HubJsonLd,
  hubPageMetadata,
} from "@/lib/seo/hub-page";
import type { TaxonomyLocation } from "@/lib/taxonomy-api";

export async function locationHubMetadata(
  kind: string,
  slug: string,
  categoryName?: string,
) {
  const detail = await fetchTaxonomyLocationDetailSeo(kind, slug);
  const label = detail?.location.name || slug.replace(/-/g, " ");
  const title = categoryName
    ? `${categoryName} events in ${label}`
    : `Events in ${label}`;
  const path = categoryName
    ? `/events/${kind}/${slug}/${categoryName.toLowerCase().replace(/\s+/g, "-")}`
    : `/events/${kind}/${slug}`;
  const loc = detail?.location as
    | {
        description?: string | null;
        seo_title?: string | null;
        seo_description?: string | null;
      }
    | undefined;
  return hubPageMetadata({
    title,
    description:
      loc?.seo_description ||
      loc?.description ||
      (categoryName
        ? `Discover ${categoryName} events in ${label} on Pàdéyá.`
        : locationLandingSubtext(label)),
    path,
    seoTitle: loc?.seo_title,
    seoDescription: loc?.seo_description,
  });
}

export async function LocationHubPage({
  kind,
  slug,
  hubKind,
  categorySlug,
  categoryName,
}: {
  kind: string;
  slug: string;
  hubKind: HubKind;
  categorySlug?: string;
  categoryName?: string;
}) {
  const detail = await fetchTaxonomyLocationDetailSeo(kind, slug);
  const label = detail?.location.name || slug.replace(/-/g, " ");
  const locMeta = detail?.location as
    | { description?: string | null; seo_description?: string | null }
    | undefined;
  const description =
    locMeta?.seo_description ||
    locMeta?.description ||
    (categoryName
      ? `Discover ${categoryName} events in ${label} on Pàdéyá.`
      : locationLandingSubtext(label));
  const path = categorySlug
    ? `/events/${kind}/${slug}/${categorySlug}`
    : `/events/${kind}/${slug}`;
  const crumbs = buildLocationTrail(
    (detail?.ancestors || []).map((a) => ({
      name: a.name,
      kind: a.kind,
      slug: a.slug,
    })),
    { name: label, kind, slug },
  );
  if (categoryName && categorySlug) {
    crumbs[crumbs.length - 1] = {
      label,
      href: `/events/${kind}/${slug}`,
    };
    crumbs.push({ label: categoryName });
  }

  const ancestors = (detail?.ancestors || []) as TaxonomyLocation[];
  const children = (detail?.children || []) as TaxonomyLocation[];
  const siblings = (detail?.siblings || []) as TaxonomyLocation[];

  const isPremiumLanding =
    !categorySlug &&
    (hubKind === "city" ||
      hubKind === "state" ||
      hubKind === "country" ||
      hubKind === "area");

  return (
    <>
      <HubJsonLd
        name={
          categoryName
            ? `${categoryName} events in ${label}`
            : `Events in ${label}`
        }
        description={description}
        path={path}
        crumbs={crumbs}
      />
      {isPremiumLanding ? (
        <LocationLandingClient
          kind={kind}
          slug={slug}
          name={label}
          crumbs={crumbs}
          childLocations={children}
          siblingLocations={siblings}
          ancestors={ancestors}
        />
      ) : categorySlug && categoryName ? (
        <CategoryLandingClient
          categorySlug={categorySlug}
          categoryName={categoryName}
          categoryDescription={description}
          crumbs={crumbs}
          citySlug={kind === "city" ? slug : undefined}
          cityName={kind === "city" ? label : undefined}
          locationKind={kind !== "city" ? kind : undefined}
          locationSlug={kind !== "city" ? slug : undefined}
          locationName={kind !== "city" ? label : undefined}
        />
      ) : (
        <DiscoveryHubClient
          kind={hubKind}
          locationKind={kind}
          locationSlug={slug}
          locationName={label}
          locationAncestors={ancestors}
          locationChildren={children}
          citySlug={kind === "city" ? slug : undefined}
          cityName={kind === "city" ? label : undefined}
          categorySlug={categorySlug}
          categoryName={categoryName}
        />
      )}
    </>
  );
}
