import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { MerchProductDetailView } from "@/components/merch/marketplace/MerchProductDetailView";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import { brand } from "@/lib/brand";
import { NOINDEX_ROBOTS } from "@/lib/seo/noindex";
import {
  isMerchProductSchemaEligible,
  merchProductJsonLd,
} from "@/lib/seo/merch-metadata";
import { breadcrumbJsonLd, JsonLdScript } from "@/lib/seo/jsonld";
import { buildPageMetadata, siteOrigin } from "@/lib/seo/site";
import { resolvePublicAssetUrl } from "@/lib/seo/public-asset";
import type { MarketplaceProduct } from "@/lib/types/merch";

type PageProps = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ h?: string }>;
};

async function loadProduct(
  slug: string,
  hostSlug?: string,
): Promise<MarketplaceProduct | null> {
  try {
    const params = new URLSearchParams();
    if (hostSlug) params.set("h", hostSlug);
    const suffix = params.size ? `?${params.toString()}` : "";
    const res = await fetch(
      `${getApiBaseUrl()}${getApiPrefix()}/merch/${encodeURIComponent(slug)}${suffix}`,
      { next: { revalidate: 60 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as MarketplaceProduct;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
  searchParams,
}: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const { h } = await searchParams;
  const product = await loadProduct(slug, h);
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
    resolvePublicAssetUrl(product.cover_image_url) ||
    resolvePublicAssetUrl(product.image_url) ||
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

export default async function MerchProductPage({
  params,
  searchParams,
}: PageProps) {
  const { slug } = await params;
  const { h } = await searchParams;
  const product = await loadProduct(slug, h);
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
      <MerchProductDetailView
        slug={slug}
        hostSlug={h}
        initialProduct={product}
      />
    </>
  );
}
