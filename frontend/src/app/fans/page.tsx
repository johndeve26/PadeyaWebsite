import type { Metadata } from "next";

import { FansDirectory } from "@/components/passport/FansDirectory";
import { brand } from "@/lib/brand";

export const metadata: Metadata = {
  title: `Fans · Fan Passport · ${brand.name}`,
  description:
    "Discover public Fan Passports on Pàdéyá — fans who attend verified events, follow hosts, earn badges, and optionally use Fan Connect.",
};

export const revalidate = 180;

export default function FansDirectoryPage() {
  return <FansDirectory />;
}
