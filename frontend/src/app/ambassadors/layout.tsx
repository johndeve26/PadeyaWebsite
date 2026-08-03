import type { Metadata } from "next";

import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Become a Pàdéyá Ambassador | Share Events and Earn Commission",
  description:
    "Pàdéyá-wide ambassadors promote across events and merch by default. Hosts can also enable their own event campaigns. Track clicks, sales and commission in one dashboard.",
  path: "/ambassadors",
});

export default function AmbassadorsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
