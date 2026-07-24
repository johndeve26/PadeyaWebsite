"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";

import {
  FeaturedSponsorHosts,
  SponsorBrandDirectory,
  SponsorCTA,
  SponsorHero,
  SponsorHowItWorks,
  SponsorInquiryForm,
  type SponsorInquiryFormValues,
  SponsorStats,
  SponsorTrustBlock,
  SponsorshipSlotFilters,
  SponsorshipSlotsGrid,
  SPONSOR_SLOTS_PAGE_SIZE,
} from "@/components/sponsors";
import {
  Alert,
  Button,
  Container,
  EmptyState,
  SectionHeader,
  SkeletonCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { brand } from "@/lib/brand";
import {
  enrichSponsorHosts,
  formatCompactNumber,
  summarizeSponsorHosts,
} from "@/lib/sponsor-host-presentation";
import {
  enrichSponsorshipSlots,
  filterAndSortSponsorshipSlots,
  uniqueSlotCategories,
  uniqueSlotCities,
  uniqueSlotTypes,
  type SponsorAudienceBucket,
  type SponsorBudgetRange,
  type SponsorSlotSort,
} from "@/lib/sponsor-slot-presentation";
import {
  fetchPublicSponsorshipSlots,
  fetchSponsorHosts,
  submitSponsorshipInquiry,
} from "@/lib/sponsorships-api";
import { fetchSponsorCampaigns } from "@/lib/sponsor-campaigns-api";
import {
  fetchSponsorWorkspaces,
  type SponsorWorkspace,
} from "@/lib/sponsor-profiles-api";
import {
  SPONSORSHIP_HOSTS_PATH,
  SPONSORSHIP_MARKETPLACE_PATH,
  SPONSORSHIP_OPEN_SLOTS_HASH,
} from "@/lib/sponsor-marketplace-paths";
import type { SponsorHost, SponsorshipSlot } from "@/lib/types/sponsorships";

const EMPTY_FORM: SponsorInquiryFormValues = {
  company_name: "",
  contact_name: "",
  contact_email: "",
  website: "",
  message: "",
  proposed_budget: "",
};

function SponsorsMarketplaceInner() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const hostFilter = (searchParams.get("host") || "").replace(/^@/, "").toLowerCase();
  const sponsorSlugHint = (searchParams.get("sponsor") || "").trim();

  const [slots, setSlots] = useState<SponsorshipSlot[] | null>(null);
  const [hosts, setHosts] = useState<SponsorHost[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeSlot, setActiveSlot] = useState<string | null>(null);
  const [form, setForm] = useState<SponsorInquiryFormValues>(EMPTY_FORM);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sponsorWorkspace, setSponsorWorkspace] = useState<SponsorWorkspace | null>(
    null,
  );
  const [inquiryCampaigns, setInquiryCampaigns] = useState<
    { id: string; name: string }[]
  >([]);
  const [inquiryCampaignId, setInquiryCampaignId] = useState("");

  const [search, setSearch] = useState("");
  const [city, setCity] = useState("all");
  const [category, setCategory] = useState("all");
  const [slotType, setSlotType] = useState("all");
  const [budget, setBudget] = useState<SponsorBudgetRange>("all");
  const [audience, setAudience] = useState<SponsorAudienceBucket>("all");
  const [sort, setSort] = useState<SponsorSlotSort>("recommended");
  const [visibleCount, setVisibleCount] = useState(SPONSOR_SLOTS_PAGE_SIZE);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [slotRows, hostRows] = await Promise.all([
          fetchPublicSponsorshipSlots(),
          fetchSponsorHosts().catch(() => [] as SponsorHost[]),
        ]);
        if (!active) return;
        setSlots(slotRows);
        setHosts(hostRows);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load slots");
          setSlots([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!user) {
      setSponsorWorkspace(null);
      setInquiryCampaigns([]);
      setInquiryCampaignId("");
      return;
    }
    let active = true;
    void (async () => {
      try {
        const workspaces = await fetchSponsorWorkspaces();
        if (!active || workspaces.length === 0) return;
        const ws = workspaces[0];
        setSponsorWorkspace(ws);
        const { items } = await fetchSponsorCampaigns(ws.sponsor_id);
        if (!active) return;
        setInquiryCampaigns(
          items
            .filter((c) => c.status !== "archived")
            .map((c) => ({ id: c.id, name: c.name })),
        );
      } catch {
        if (active) {
          setInquiryCampaigns([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [user]);

  useEffect(() => {
    if (!sponsorSlugHint) return;
    const label = sponsorSlugHint.replace(/-/g, " ");
    setForm((prev) => {
      if (prev.message.trim()) return prev;
      return {
        ...prev,
        message: `Hi — we're exploring a partnership with ${label} for an upcoming Pàdéyá activation. Here's our event context:`,
      };
    });
  }, [sponsorSlugHint]);

  const enrichedHosts = useMemo(() => enrichSponsorHosts(hosts), [hosts]);
  const summary = useMemo(() => summarizeSponsorHosts(enrichedHosts), [enrichedHosts]);
  const featuredHosts = useMemo(
    () =>
      [...enrichedHosts]
        .sort((a, b) => Number(b.featured) - Number(a.featured) || b.open_slots - a.open_slots)
        .slice(0, 3),
    [enrichedHosts],
  );

  const loadedSlots = useMemo(() => slots ?? [], [slots]);
  const slotsLoading = slots === null && !error;

  const enrichedSlots = useMemo(
    () => enrichSponsorshipSlots(loadedSlots, enrichedHosts),
    [loadedSlots, enrichedHosts],
  );

  const cities = useMemo(() => uniqueSlotCities(enrichedSlots), [enrichedSlots]);
  const categories = useMemo(
    () => uniqueSlotCategories(enrichedSlots),
    [enrichedSlots],
  );
  const slotTypes = useMemo(() => uniqueSlotTypes(enrichedSlots), [enrichedSlots]);

  const filteredSlots = useMemo(
    () =>
      filterAndSortSponsorshipSlots(enrichedSlots, {
        search,
        city,
        category,
        slotType,
        budget,
        audience,
        sort,
        hostUsername: hostFilter,
      }),
    [
      enrichedSlots,
      search,
      city,
      category,
      slotType,
      budget,
      audience,
      sort,
      hostFilter,
    ],
  );

  const hasActiveFilters =
    Boolean(search.trim()) ||
    city !== "all" ||
    category !== "all" ||
    slotType !== "all" ||
    budget !== "all" ||
    audience !== "all" ||
    Boolean(hostFilter);

  const filterKey = [
    search,
    city,
    category,
    slotType,
    budget,
    audience,
    sort,
    hostFilter,
  ].join("|");
  const [appliedFilterKey, setAppliedFilterKey] = useState(filterKey);
  if (appliedFilterKey !== filterKey) {
    setAppliedFilterKey(filterKey);
    setVisibleCount(SPONSOR_SLOTS_PAGE_SIZE);
  }

  function clearFilters() {
    setSearch("");
    setCity("all");
    setCategory("all");
    setSlotType("all");
    setBudget("all");
    setAudience("all");
    setSort("recommended");
    setVisibleCount(SPONSOR_SLOTS_PAGE_SIZE);
  }

  async function onInquire(slotId: string) {
    setBusy(true);
    setNote(null);
    setError(null);
    try {
      await submitSponsorshipInquiry(slotId, {
        company_name: form.company_name,
        contact_name: form.contact_name,
        contact_email: form.contact_email,
        website: form.website || undefined,
        message: form.message,
        proposed_budget: form.proposed_budget || undefined,
        campaign_id: inquiryCampaignId || undefined,
        sponsor_id: sponsorWorkspace?.sponsor_id,
      });
      setNote("Inquiry submitted. The host will follow up — nothing is auto-approved.");
      setActiveSlot(null);
      setForm(EMPTY_FORM);
      setInquiryCampaignId("");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Inquiry failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-background">
      <SponsorHero
        backgroundSrc={brand.heroImage}
        eyebrow="Sponsorship marketplace"
        title="Sponsor hosts. Reach real nights."
        description="Discover verified Pàdéyá hosts and open sponsorship slots. Brands inquire directly; hosts manage packages from their workspace."
        primaryCta={{ href: "#open-slots", label: "Browse opportunities" }}
        secondaryCta={{ href: SPONSORSHIP_HOSTS_PATH, label: "View sponsorship hosts" }}
        stats={
          <SponsorStats
            items={[
              { label: "Active hosts", value: summary.verifiedHosts || hosts.length },
              { label: "Open slots", value: loadedSlots.length },
              {
                label: "Audience reach",
                value: formatCompactNumber(summary.verifiedAttendees),
              },
              { label: "Cities", value: summary.cities },
            ]}
          />
        }
      />

      <Container className="space-y-14 py-10 sm:space-y-16 sm:py-14">
        {featuredHosts.length > 0 ? (
          <FeaturedSponsorHosts hosts={featuredHosts} />
        ) : null}

        <SponsorBrandDirectory />

        <section id="open-slots" className="scroll-mt-20 space-y-5">
          <SectionHeader
            eyebrow="Marketplace"
            title="Open sponsorship slots"
            description={
              hostFilter
                ? `Browse active packages for @${hostFilter}.`
                : "Browse active sponsor opportunities from verified hosts."
            }
            action={
              hostFilter ? (
                <Link href={`${SPONSORSHIP_MARKETPLACE_PATH}${SPONSORSHIP_OPEN_SLOTS_HASH}`}>
                  <Button variant="ghost">Clear host filter</Button>
                </Link>
              ) : (
                <Link href={SPONSORSHIP_HOSTS_PATH}>
                  <Button variant="secondary">Browse hosts</Button>
                </Link>
              )
            }
          />

          <SponsorshipSlotFilters
            search={search}
            onSearchChange={setSearch}
            city={city}
            cities={cities}
            onCityChange={setCity}
            category={category}
            categories={categories}
            onCategoryChange={setCategory}
            slotType={slotType}
            slotTypes={slotTypes}
            onSlotTypeChange={setSlotType}
            budget={budget}
            onBudgetChange={setBudget}
            audience={audience}
            onAudienceChange={setAudience}
            sort={sort}
            onSortChange={setSort}
            onClear={clearFilters}
            hasActiveFilters={hasActiveFilters && !hostFilter}
          />

          {error ? (
            <Alert tone="danger" title="Could not load slots">
              {error}
            </Alert>
          ) : null}
          {note ? (
            <Alert tone="success" title="Inquiry sent">
              {note}
            </Alert>
          ) : null}

          {slotsLoading ? (
            <div className="grid gap-3 lg:grid-cols-2">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
          ) : filteredSlots.length === 0 ? (
            <EmptyState
              title={
                hasActiveFilters || hostFilter
                  ? "No sponsorship slots match your filters."
                  : "No published sponsorship slots yet"
              }
              description={
                hasActiveFilters || hostFilter
                  ? "Try clearing filters or browsing verified hosts."
                  : "Verified hosts can list packages here. Browse hosts meanwhile."
              }
              action={
                hasActiveFilters || hostFilter ? (
                  hostFilter ? (
                    <Link href={`${SPONSORSHIP_MARKETPLACE_PATH}${SPONSORSHIP_OPEN_SLOTS_HASH}`}>
                      <Button variant="secondary">Clear filters</Button>
                    </Link>
                  ) : (
                    <Button variant="secondary" onClick={clearFilters}>
                      Clear filters
                    </Button>
                  )
                ) : (
                  <Link href={SPONSORSHIP_HOSTS_PATH}>
                    <Button variant="secondary">Browse verified hosts</Button>
                  </Link>
                )
              }
            />
          ) : (
            <SponsorshipSlotsGrid
              slots={filteredSlots}
              visibleCount={visibleCount}
              onShowMore={() =>
                setVisibleCount((n) => n + SPONSOR_SLOTS_PAGE_SIZE)
              }
              activeSlotId={activeSlot}
              onToggleInquiry={(id) =>
                setActiveSlot(activeSlot === id ? null : id)
              }
              renderInquiryForm={(slot) => (
                <SponsorInquiryForm
                  slot={slot}
                  values={form}
                  onChange={setForm}
                  onSubmit={() => void onInquire(slot.id)}
                  busy={busy}
                  campaigns={inquiryCampaigns}
                  campaignId={inquiryCampaignId}
                  onCampaignChange={setInquiryCampaignId}
                />
              )}
            />
          )}
        </section>

        <SponsorHowItWorks />
        <SponsorTrustBlock />
        <SponsorCTA />
      </Container>
    </main>
  );
}

export default function SponsorsMarketplacePage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-background">
          <Container className="py-16">
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          </Container>
        </main>
      }
    >
      <SponsorsMarketplaceInner />
    </Suspense>
  );
}
