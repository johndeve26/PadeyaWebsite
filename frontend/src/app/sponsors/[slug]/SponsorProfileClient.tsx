"use client";

import { PublicSponsorProfileView } from "@/components/sponsors/PublicSponsorProfileView";
import type { SponsorPublicProfile } from "@/lib/sponsor-profiles-api";

export function SponsorProfileClient({
  profile,
}: {
  profile: SponsorPublicProfile;
}) {
  return <PublicSponsorProfileView profile={profile} />;
}
