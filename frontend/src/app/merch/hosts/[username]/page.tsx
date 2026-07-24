import type { Metadata } from "next";

import { MerchHostShopView } from "@/components/merch/marketplace/MerchHostShopView";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import { brand } from "@/lib/brand";
import { buildPageMetadata } from "@/lib/seo/site";
import type { MarketplaceHostShopDetail } from "@/lib/types/merch";

type PageProps = {
  params: Promise<{ username: string }>;
};

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { username } = await params;
  const clean = decodeURIComponent(username).replace(/^@/, "");
  return buildPageMetadata({
    title: `@${clean} merch shop · ${brand.name}`,
    description: `Shop official merch from @${clean} on ${brand.name}.`,
    path: `/merch/hosts/${clean}`,
  });
}

async function loadHostShop(
  username: string,
): Promise<MarketplaceHostShopDetail | null> {
  try {
    const res = await fetch(
      `${getApiBaseUrl()}${getApiPrefix()}/merch/hosts/${encodeURIComponent(username)}`,
      { next: { revalidate: 60 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as MarketplaceHostShopDetail;
  } catch {
    return null;
  }
}

export default async function MerchHostShopPage({ params }: PageProps) {
  const { username } = await params;
  const clean = decodeURIComponent(username).replace(/^@/, "");
  const initialShop = await loadHostShop(clean);
  return <MerchHostShopView key={clean} username={clean} initialShop={initialShop} />;
}
