import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

export const metadata: Metadata = privateAreaMetadata("Checkout");

/** Event ticket checkout — never indexable (Offer schema may still link here). */
export default function EventCheckoutLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
