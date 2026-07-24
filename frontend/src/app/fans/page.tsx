import type { Metadata } from "next";

import { FansDirectory } from "@/components/passport/FansDirectory";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Fans · Fan Passport",
  description:
    "Discover public Fan Passports on Pàdéyá — fans who attend verified events, follow hosts, earn badges, and optionally use Fan Connect.",
  path: "/fans",
});

export const revalidate = 180;

export default function FansDirectoryPage() {
  return <FansDirectory />;
}
