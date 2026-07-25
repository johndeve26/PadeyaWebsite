import { CategoryLandingClient } from "@/components/discovery/CategoryLandingClient";
import { DiscoveryHubClient } from "@/components/discovery/DiscoveryHubClient";
import { LocationLandingClient } from "@/components/discovery/LocationLandingClient";
import type { HubKind } from "@/lib/discovery/hub-kind";
import { locationLandingSubtext } from "@/lib/discovery/location-landing";
import { fetchPublicEventsServer } from "@/lib/events/public-server";
import { buildLocationTrail } from "@/lib/marketplace-breadcrumbs";
import {
  evaluateCityCategoryHubEligibility,
  evaluateLocationHubEligibility,
  locationHubFallbackCopy,
  locationHubIntroParagraph,
} from "@/lib/seo/hub-eligibility";
import {
  fetchTaxonomyLocationDetailSeo,
  HubJsonLd,
  hubPageMetadata,
} from "@/lib/seo/hub-page";
import type { TaxonomyLocation } from "@/lib/taxonomy-api";

type LocSeo = TaxonomyLocation & {
  description?: string | null;
};

export async function locationHubMetadata(
  kind: string,
  slug: string,
  categoryName?: string,
  categorySlug?: string,
) {
  const [detail, events] = await Promise.all([
    fetchTaxonomyLocationDetailSeo(kind, slug),
    fetchPublicEventsServer({
      location_kind: kind,
      location_slug: slug,
      ...(categorySlug ? { category: categorySlug } : {}),
    }),
  ]);

  const loc = detail?.location as LocSeo | undefined;
  const label = loc?.name || slug.replace(/-/g, " ");
  const parentName =
    detail?.ancestors?.[detail.ancestors.length - 1]?.name || null;
  const fallback = locationHubFallbackCopy({
    locationName: label,
    kind,
    parentName,
    categoryName,
  });

  const eligibility = categorySlug
    ? evaluateCityCategoryHubEligibility({
        cityExists: Boolean(detail?.location),
        cityActive: loc?.is_active,
        categoryExists: Boolean(categoryName || categorySlug),
        categoryActive: true,
        eventCount: events.length,
        citySeoIndexMode: loc?.seo_index_mode,
      })
    : evaluateLocationHubEligibility({
        exists: Boolean(detail?.location),
        isActive: loc?.is_active,
        kind,
        eventCount: events.length,
        seoIndexMode: loc?.seo_index_mode,
      });

  const path = categorySlug
    ? `/events/${kind}/${slug}/${categorySlug}`
    : `/events/${kind}/${slug}`;

  return hubPageMetadata({
    title: fallback.title,
    description:
      loc?.seo_description ||
      loc?.description ||
      fallback.description ||
      locationLandingSubtext(label),
    path,
    seoTitle: loc?.seo_title
      ? categoryName
        ? `${loc.seo_title} · ${categoryName}`
        : loc.seo_title
      : undefined,
    seoDescription: loc?.seo_description,
    noIndex: !eligibility.indexable,
    noIndexFollow: true,
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
  const [detail, events] = await Promise.all([
    fetchTaxonomyLocationDetailSeo(kind, slug),
    fetchPublicEventsServer({
      location_kind: kind,
      location_slug: slug,
      ...(categorySlug ? { category: categorySlug } : {}),
    }),
  ]);

  const loc = detail?.location as LocSeo | undefined;
  const label = loc?.name || slug.replace(/-/g, " ");
  const parentName =
    detail?.ancestors?.[detail.ancestors.length - 1]?.name || null;
  const fallback = locationHubFallbackCopy({
    locationName: label,
    kind,
    parentName,
    categoryName,
  });
  const description =
    loc?.seo_description ||
    loc?.description ||
    fallback.description ||
    locationLandingSubtext(label);
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

  const categoryNames = [
    ...new Set(
      events
        .map((e) => e.category?.name)
        .filter((n): n is string => Boolean(n)),
    ),
  ].slice(0, 4);

  const intro = locationHubIntroParagraph({
    locationName: label,
    parentName,
    eventCount: events.length,
    categoryNames,
    curatedIntro: loc?.intro_content,
  });

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
          introContent={intro}
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
