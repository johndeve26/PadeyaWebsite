import { redirect } from "next/navigation";

import { SPONSORSHIP_HOSTS_PATH } from "@/lib/sponsor-marketplace-paths";

export default function SponsorHostsLegacyRedirectPage() {
  redirect(SPONSORSHIP_HOSTS_PATH);
}
