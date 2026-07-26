import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { MerchProductDetailView } from "@/components/merch/marketplace/MerchProductDetailView";
import { brand } from "@/lib/brand";
import { getPublicMerchBySlug } from "@/lib/public-loaders/entities";
import { NOINDEX_ROBOTS } from "@/lib/seo/noindex";
import {
  isMerchProductSchemaEligible,
  merchProductJsonLd,
} from "@/lib/seo/merch-metadata";
import { breadcrumbJsonLd, JsonLdScript } from "@/lib/seo/jsonld";
import { buildPageMetadata, siteOrigin } from "@/lib/seo/site";
import { resolveOgImageUrl } from "@/lib/seo/public-asset";

/**
 * ISR for canonical product URLs. Host filter `?h=` is applied client-side so
 * this route stays cacheable (searchParams would force private no-store).
 */
export const revalidate = 60;

type PageProps = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const product = await getPublicMerchBySlug(slug);
  if (!product) {
    return {
      title: `Merch · ${brand.name}`,
      robots: NOINDEX_ROBOTS,
    };
  }

  const title = `${product.name}${product.host_name ? ` · ${product.host_name}` : ""}`;
  const description =
    product.short_description ||
    product.description ||
    `Shop ${product.name} on ${brand.name}.`;
  const image =
    resolveOgImageUrl(product.cover_image_url) ||
    resolveOgImageUrl(product.image_url) ||
    undefined;
  const indexable = product.indexable !== false;

  return {
    ...buildPageMetadata({
      title,
      description,
      path: `/merch/${slug}`,
      image,
      noIndex: !indexable,
    }),
  };
}

export default async function MerchProductPage({ params }: PageProps) {
  const { slug } = await params;
  const product = await getPublicMerchBySlug(slug);
  if (!product) notFound();

  const productSchema = merchProductJsonLd(product);
  const showBreadcrumbLd = isMerchProductSchemaEligible(product);
  const crumbs = [
    { label: "Home", href: "/" },
    { label: "Merch", href: "/merch" },
    { label: product.name },
  ];

  return (
    <>
      {productSchema ? <JsonLdScript data={productSchema} /> : null}
      {showBreadcrumbLd ? (
        <JsonLdScript data={breadcrumbJsonLd(crumbs, siteOrigin())} />
      ) : null}
      <Suspense fallback={null}>
        <MerchProductDetailView slug={slug} initialProduct={product} />
      </Suspense>
    </>
  );
}
