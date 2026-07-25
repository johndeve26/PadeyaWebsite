import type { Metadata } from "next";

import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Ambassadors",
  description:
    "Earn as a Pàdéyá Ambassador — share event links, track verified sales, and unlock host-set rewards without host dashboard access.",
  path: "/ambassadors",
});

export default function AmbassadorsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
