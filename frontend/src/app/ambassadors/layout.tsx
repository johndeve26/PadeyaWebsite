import type { Metadata } from "next";

import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Become a Pàdéyá Ambassador | Share Events and Earn Commission",
  description:
    "Join eligible Pàdéyá-wide referral programs or promote event campaigns from hosts. Share referral links and track clicks, sales and commission in one dashboard.",
  path: "/ambassadors",
});

export default function AmbassadorsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
