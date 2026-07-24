import type { Metadata } from "next";

import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = {
  ...buildPageMetadata({
    title: "Payment success",
    description: "Your Pàdéyá checkout payment was received.",
    path: "/checkout/success",
    noIndex: true,
  }),
};

export default function CheckoutSuccessLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
