"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import {
  HostSponsorCard,
  SponsorFilterBar,
  SponsorHero,
  SponsorHowItWorks,
  SponsorStats,
  SponsorTrustBlock,
} from "@/components/sponsors";
import { Button, Container, EmptyState, SectionHeader } from "@/components/ui";
import { brand } from "@/lib/brand";
import {
  enrichSponsorHosts,
  filterAndSortSponsorHosts,
  formatCompactNumber,
  summarizeSponsorHosts,
  uniqueHostCategories,
  uniqueHostCities,
  type SponsorHostSort,
} from "@/lib/sponsor-host-presentation";
import {
  SPONSORSHIP_MARKETPLACE_PATH,
  sponsorshipMarketplaceUrl,
} from "@/lib/sponsor-marketplace-paths";

export function SponsorHostsMarketplace({
  initialHosts,
}: {
  initialHosts: SponsorHost[];
}) {
  const [search, setSearch] = useState("");
  const [city, setCity] = useState("all");
  const [category, setCategory] = useState("all");
  const [sort, setSort] = useState<SponsorHostSort>("slots");
  const [verifiedOnly, setVerifiedOnly] = useState(true);

  const enriched = useMemo(() => enrichSponsorHosts(initialHosts), [initialHosts]);
  const summary = useMemo(() => summarizeSponsorHosts(enriched), [enriched]);
  const cities = useMemo(() => uniqueHostCities(enriched), [enriched]);
  const categories = useMemo(() => uniqueHostCategories(enriched), [enriched]);
  const filtered = useMemo(
    () =>
      filterAndSortSponsorHosts(enriched, {
        search,
        city,
        category,
        verifiedOnly,
        sort,
      }),
    [enriched, search, city, category, verifiedOnly, sort],
  );

  return (
    <main className="min-h-screen bg-background">
      <SponsorHero
        backgroundSrc={brand.heroImage}
        eyebrow="Sponsor verified event creators"
        title="Partner with hosts who can prove their audience."
        description="Browse verified Pàdéyá hosts with event history, checked-in attendance, Legacy reputation, and active sponsorship slots."
        primaryCta={{ href: SPONSORSHIP_MARKETPLACE_PATH, label: "Browse slots" }}
        secondaryCta={{ href: "#how-sponsorship-works", label: "How sponsorship works" }}
        stats={
          <SponsorStats
            items={[
              { label: "Verified hosts", value: summary.verifiedHosts },
              { label: "Open sponsorship slots", value: summary.openSlots },
              {
                label: "Verified attendees reached",
                value: formatCompactNumber(summary.verifiedAttendees),
              },
              { label: "Cities covered", value: summary.cities },
            ]}
          />
        }
      />

      <section className="relative z-10 -mt-6 pb-4 sm:-mt-8">
        <Container>
          <SponsorFilterBar
            search={search}
            onSearchChange={setSearch}
            city={city}
            cities={cities}
            onCityChange={setCity}
            category={category}
            categories={categories}
            onCategoryChange={setCategory}
            sort={sort}
            onSortChange={setSort}
            verifiedOnly={verifiedOnly}
            onVerifiedOnlyChange={setVerifiedOnly}
            className="shadow-[var(--shadow-strong)]"
          />
        </Container>
      </section>

      <Container className="space-y-12 pb-14 pt-6 sm:pb-16 sm:pt-8">
        <section className="space-y-5">
          <SectionHeader
            eyebrow="Marketplace"
            title="Sponsorship-ready hosts"
            description="Filter by city, category, and Legacy signal. Open a Legacy Page or jump straight into open slots."
            action={
              <Link href={SPONSORSHIP_MARKETPLACE_PATH}>
                <Button size="lg" variant="dark">
                  View all slots
                </Button>
              </Link>
            }
          />

          {filtered.length === 0 ? (
            <EmptyState
              title="No sponsorship-ready hosts yet"
              description="When verified hosts turn on sponsorships and publish slots, they appear here with Legacy proof and package availability."
              action={
                <Link href={SPONSORSHIP_MARKETPLACE_PATH}>
                  <Button size="lg">Browse sponsorship slots</Button>
                </Link>
              }
            />
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {filtered.map((host) => (
                <HostSponsorCard
                  key={host.host_id}
                  host={host}
                  featured={host.featured}
                />
              ))}
            </div>
          )}
        </section>

        <div id="how-sponsorship-works" className="rounded-[var(--radius-xl)] bg-card px-5 py-8 sm:px-8 sm:py-10">
          <SponsorHowItWorks />
        </div>

        <SponsorTrustBlock />
      </Container>
    </main>
  );
}
