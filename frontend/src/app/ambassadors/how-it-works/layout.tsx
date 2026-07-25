import type { Metadata } from "next";

import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "How Ambassadors work",
  description:
    "How Pàdéyá Ambassadors earn: verified paid referrals only, host-set commissions and rewards, no buyer private data.",
  path: "/ambassadors/how-it-works",
});

export default function AmbassadorsHowItWorksLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
