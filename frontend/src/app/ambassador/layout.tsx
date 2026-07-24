import type { Metadata } from "next";

import { privateAreaMetadata } from "@/lib/seo/noindex";

export const metadata: Metadata = privateAreaMetadata("Ambassadors");

/** Legacy /ambassador → dashboard redirect tree — keep noindex. */
export default function AmbassadorLegacyLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
