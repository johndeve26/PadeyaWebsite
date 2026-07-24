import type { Metadata } from "next";

import { MerchVaultView } from "@/components/merch/marketplace/MerchVaultView";
import { brand } from "@/lib/brand";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: `Vault exclusives · ${brand.name}`,
  description: `Vault-exclusive merch teasers from ${brand.name} hosts. Unlock Vault access to purchase.`,
  path: "/merch/vault",
});

export default function MerchVaultPage() {
  return <MerchVaultView />;
}
