import type { Metadata } from "next";

import { MerchDropsView } from "@/components/merch/marketplace/MerchDropsView";
import { brand } from "@/lib/brand";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: `Post-event drops · ${brand.name}`,
  description: `Limited post-event merch drops from ${brand.name} hosts for ticket buyers, checked-in fans, VIP, and Vault members.`,
  path: "/merch/drops",
});

export default function MerchDropsPage() {
  return <MerchDropsView />;
}
