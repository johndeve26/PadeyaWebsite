"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import {
  Container,
  SectionHeader,
  Select,
  SkeletonCard,
} from "@/components/ui";
import {
  SponsorshipSlotsGrid,
  SPONSOR_SLOTS_PAGE_SIZE,
} from "@/components/sponsors";
import { fetchCampaignRecommendations, fetchSponsorCampaigns } from "@/lib/sponsor-campaigns-api";
import { enrichSponsorHosts } from "@/lib/sponsor-host-presentation";
import {
  enrichSponsorshipSlots,
  filterAndSortSponsorshipSlots,
  type SponsorSlotSort,
} from "@/lib/sponsor-slot-presentation";
import { fetchPublicSponsorshipSlots, fetchSponsorHosts } from "@/lib/sponsorships-api";
import { SPONSORSHIP_MARKETPLACE_PATH } from "@/lib/sponsor-marketplace-paths";
import type { SponsorHost, SponsorshipSlot } from "@/lib/types/sponsorships";

export default function SponsorOpportunitiesPage() {
  const { active } = useSponsorWorkspace();
  const sponsorId = active?.sponsor_id ?? null;

  const [slots, setSlots] = useState<SponsorshipSlot[] | null>(null);
  const [hosts, setHosts] = useState<SponsorHost[]>([]);
  const [visibleCount, setVisibleCount] = useState(SPONSOR_SLOTS_PAGE_SIZE);
  const [campaigns, setCampaigns] = useState<{ id: string; name: string }[]>([]);
  const [campaignId, setCampaignId] = useState("");
  const [campaignScores, setCampaignScores] = useState<Record<string, number>>({});
  const [sort, setSort] = useState<SponsorSlotSort>("recommended");

  useEffect(() => {
    void (async () => {
      const [slotRows, hostRows] = await Promise.all([
        fetchPublicSponsorshipSlots(),
        fetchSponsorHosts().catch(() => [] as SponsorHost[]),
      ]);
      setSlots(slotRows);
      setHosts(hostRows);
    })();
  }, []);

  useEffect(() => {
    if (!sponsorId) return;
    void (async () => {
      const { items } = await fetchSponsorCampaigns(sponsorId);
      setCampaigns(
        items
          .filter((c) => c.status !== "archived")
          .map((c) => ({ id: c.id, name: c.name })),
      );
    })();
  }, [sponsorId]);

  useEffect(() => {
    if (!sponsorId || !campaignId) {
      setCampaignScores({});
      if (sort === "campaign_recommended") setSort("recommended");
      return;
    }
    void (async () => {
      const { items } = await fetchCampaignRecommendations(sponsorId, campaignId);
      const scores: Record<string, number> = {};
      for (const row of items) {
        if (row.item_type === "sponsorship_slot") {
          scores[row.item_id] = row.score;
        }
      }
      setCampaignScores(scores);
      setSort("campaign_recommended");
    })();
  }, [campaignId, sponsorId]);

  const enrichedHosts = enrichSponsorHosts(hosts);
  const enrichedSlots = enrichSponsorshipSlots(slots ?? [], enrichedHosts);
  const filtered = useMemo(
    () =>
      filterAndSortSponsorshipSlots(enrichedSlots, {
        search: "",
        city: "all",
        category: "all",
        slotType: "all",
        budget: "all",
        audience: "all",
        sort,
        hostUsername: "",
        campaignScores,
      }),
    [campaignScores, enrichedSlots, sort],
  );

  return (
    <Container className="space-y-8 py-6">
      <SectionHeader
        eyebrow="Home"
        title="Opportunities"
        description="Browse open sponsorship slots. Optional campaign recommendations use rules-only scoring — no AI and no auto-contact."
        action={
          <Link href="/sponsor/saved">
            <span className="text-sm font-semibold text-accent underline">
              View saved
            </span>
          </Link>
        }
      />
      {sponsorId && campaigns.length > 0 ? (
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm">
            <span className="font-semibold">Recommended for campaign</span>
            <Select
              className="mt-1 block min-w-[220px]"
              value={campaignId}
              onChange={(e) => setCampaignId(e.target.value)}
            >
              <option value="">All opportunities</option>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </label>
          <label className="text-sm">
            <span className="font-semibold">Sort</span>
            <Select
              className="mt-1 block"
              value={sort}
              onChange={(e) => setSort(e.target.value as SponsorSlotSort)}
            >
              <option value="recommended">Marketplace recommended</option>
              <option value="campaign_recommended" disabled={!campaignId}>
                Recommended for campaign
              </option>
              <option value="newest">Newest</option>
              <option value="price_asc">Price (low)</option>
            </Select>
          </label>
        </div>
      ) : null}
      {slots === null ? (
        <SkeletonCard />
      ) : (
        <SponsorshipSlotsGrid
          slots={filtered}
          visibleCount={visibleCount}
          onShowMore={() => setVisibleCount((n) => n + SPONSOR_SLOTS_PAGE_SIZE)}
          activeSlotId={null}
          onToggleInquiry={() => {}}
          renderInquiryForm={() => null}
        />
      )}
      <p className="text-sm text-muted-foreground">
        More hosts and filters on the public{" "}
        <Link href={SPONSORSHIP_MARKETPLACE_PATH} className="text-accent underline">
          sponsorship marketplace
        </Link>
        .
      </p>
    </Container>
  );
}
