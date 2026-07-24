import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

export const metadata: Metadata = privateAreaMetadata("Merch checkout");

export default function MerchHostCheckoutLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
