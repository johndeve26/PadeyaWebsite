import { fetchMyEvents } from "@/lib/events-api";
import {
  buildRoadmapItems,
  type RoadmapItem,
} from "@/lib/host-roadmap";
import { fetchMyHost } from "@/lib/hosts-api";
import { fetchHostTeamMembers } from "@/lib/hosts-lifecycle-api";
import { fetchMyLegacyPage } from "@/lib/legacy-api";
import { fetchAllHostMerchProducts } from "@/lib/merch-api";
import { fetchHostCampaigns } from "@/lib/promos-api";
import { fetchHostSponsorshipSlots } from "@/lib/sponsorships-api";

/** Loads host data and returns inferred roadmap checklist items. */
export async function loadHostRoadmapItems(): Promise<RoadmapItem[]> {
  const [host, legacy, events, teamMembers, merch, campaigns, slots] =
    await Promise.all([
      fetchMyHost().catch(() => null),
      fetchMyLegacyPage().catch(() => null),
      fetchMyEvents().catch(() => []),
      fetchHostTeamMembers(false).catch(() => []),
      fetchAllHostMerchProducts().catch(() => []),
      fetchHostCampaigns().catch(() => []),
      fetchHostSponsorshipSlots().catch(() => []),
    ]);

  return buildRoadmapItems({
    host,
    legacy,
    events,
    teamMemberCount: teamMembers.length,
    merchProductCount: merch.length,
    campaignCount: campaigns.length,
    sponsorshipSlotCount: slots.length,
  });
}
