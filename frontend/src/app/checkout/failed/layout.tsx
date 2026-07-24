import type { Metadata } from "next";

import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = {
  ...buildPageMetadata({
    title: "Payment failed",
    description: "Your Pàdéyá checkout payment did not complete.",
    path: "/checkout/failed",
    noIndex: true,
  }),
};

export default function CheckoutFailedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
