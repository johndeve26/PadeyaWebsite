import type { Metadata } from "next";

import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Support",
  description:
    "Pàdéyá Support Center — get help with tickets, refunds, account safety, hosting, and Fan Passport.",
  path: "/support",
});

/** Public Support Center routes — no staff gate. Staff shell lives under `(staff)`. */
export default function SupportPublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
