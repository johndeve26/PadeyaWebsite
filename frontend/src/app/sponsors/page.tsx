import { redirect } from "next/navigation";

import { SPONSORSHIP_MARKETPLACE_PATH } from "@/lib/sponsor-marketplace-paths";

/** Legacy URL — marketplace lives at `/sponsorships`. Brand profiles stay at `/sponsors/[slug]`. */
export default function SponsorsMarketplaceRedirectPage() {
  redirect(SPONSORSHIP_MARKETPLACE_PATH);
}
