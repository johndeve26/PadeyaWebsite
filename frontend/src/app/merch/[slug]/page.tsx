import type { Metadata } from "next";

import { MerchProductDetailView } from "@/components/merch/marketplace/MerchProductDetailView";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import { brand } from "@/lib/brand";
import { buildPageMetadata } from "@/lib/seo/site";
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
    return buildPageMetadata({
      title: `Merch · ${brand.name}`,
      description: `Shop host merch on ${brand.name}.`,
      path: `/merch/${slug}`,
    });
  }

  const title = `${product.name}${product.host_name ? ` · ${product.host_name}` : ""}`;
  const description =
    product.short_description ||
    product.description ||
    `Shop ${product.name} on ${brand.name}.`;
  const image = product.cover_image_url || product.image_url || undefined;
  const indexable = product.indexable !== false;

  return {
    ...buildPageMetadata({
      title,
      description,
      path: `/merch/${slug}`,
      image,
    }),
    robots: indexable
      ? { index: true, follow: true }
      : { index: false, follow: true },
  };
}

export default async function MerchProductPage({
  params,
  searchParams,
}: PageProps) {
  const { slug } = await params;
  const { h } = await searchParams;
  return <MerchProductDetailView slug={slug} hostSlug={h} />;
}
