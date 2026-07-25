import type { Metadata } from "next";

import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Ambassador events",
  description:
    "Browse Pàdéyá events open to Ambassadors — share verified referral links and earn on paid ticket sales.",
  path: "/ambassadors/events",
});

export default function AmbassadorsEventsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
