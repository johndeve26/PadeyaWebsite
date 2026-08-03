import type { Metadata } from "next";

import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Become a Pàdéyá Ambassador | Share Events and Earn Commission",
  description:
    "Join eligible Pàdéyá-wide programs or promote host event campaigns. Share referral links and track host-funded and Pàdéyá-funded earnings in one dashboard.",
  path: "/ambassadors",
});

export default function AmbassadorsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
