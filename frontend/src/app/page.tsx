import type { Metadata } from "next";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Suspense } from "react";

import { ReferralLandingTracker } from "@/components/ambassadors/ReferralLandingTracker";
import { HomeBlogTeaser } from "@/components/home/HomeBlogTeaser";
import { HomeDiscoveryRails } from "@/components/home/HomeDiscoveryRails";
import { HomeForFans } from "@/components/home/HomeForFans";
import { HomeLegacyCta } from "@/components/home/HomeLegacyCta";
import { HomeNearbyEventsSection } from "@/components/home/HomeNearbyEventsSection";
import { HomePadeyaPicks } from "@/components/home/HomePadeyaPicks";
import {
  Button,
  Container,
  HeroSection,
  Logo,
  SkeletonCard,
} from "@/components/ui";
import { brand } from "@/lib/brand";
import { loadHomepagePublicData } from "@/lib/home/load-homepage-public";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: brand.name,
  description: `${brand.tagline} Tickets, Fan Passport, Host Legacy, merch, Vault, ambassadors, and sponsorships, built for the night.`,
  path: "/",
});

/** ISR — aligns with PUBLIC_REVALIDATE.featured (must be a literal for Next). */
export const revalidate = 120;

/** Client taxonomy — deferred so above-fold public rails paint first. */
const HomeBrowseTaxonomy = dynamic(
  () =>
    import("@/components/home/HomeBrowseTaxonomy").then(
      (m) => m.HomeBrowseTaxonomy,
    ),
  {
    loading: () => (
      <section className="bg-background py-10">
        <Container>
          <div className="h-40 animate-pulse rounded-[var(--radius-xl)] bg-muted" />
        </Container>
      </section>
    ),
  },
);

function BlogFallback() {
  return (
    <section className="bg-background py-10">
      <Container className="grid gap-4 sm:grid-cols-3">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </Container>
    </section>
  );
}

export default async function HomePage() {
  const data = await loadHomepagePublicData();
  const nearbySeed =
    data.defaultCityEvents.length > 0 ? data.defaultCityEvents : data.featured;

  return (
    <main className="min-w-0 overflow-x-clip">
      <ReferralLandingTracker />

      <HeroSection
        minHeight="default"
        backgroundSrc={brand.heroImage}
        backgroundAlt=""
      >
        <Logo
          variant="dark"
          height={44}
          href={undefined}
          className="padeya-hero-brand drop-shadow-[0_2px_24px_rgb(0_0_0_/0.55)]"
        />
        <div className="max-w-3xl space-y-4 sm:space-y-5">
          <h1 className="padeya-hero-brand text-balance text-[1.75rem] font-extrabold leading-tight tracking-tight [text-shadow:0_2px_28px_rgb(0_0_0_/_0.55)] sm:text-5xl sm:leading-[1.08] md:text-[3.25rem] md:leading-[1.05]">
            {brand.tagline}
          </h1>
          <p className="max-w-2xl text-pretty text-base leading-relaxed text-paper/85 sm:text-lg">
            Everything events, all in one place. Discover experiences, sell
            verified tickets, retain loyal fans, and grow your event ecosystem.
          </p>
          <div className="flex flex-col gap-3 pt-0.5 sm:flex-row sm:flex-wrap">
            <Link href="/events" className="w-full sm:w-auto">
              <Button size="lg" className="w-full sm:w-auto">
                Explore events
              </Button>
            </Link>
            <Link href="/host/events/new" className="w-full sm:w-auto">
              <Button
                size="lg"
                variant="outline-dark"
                className="w-full sm:w-auto"
              >
                Create event
              </Button>
            </Link>
          </div>
        </div>
      </HeroSection>

      <HomePadeyaPicks
        initialEvents={data.picks}
        placementEventIds={data.placementEventIds}
      />

      <HomeNearbyEventsSection
        initialEvents={nearbySeed}
        defaultCityLabel={data.defaultCityLabel}
      />

      <HomeDiscoveryRails initialEvents={data.railPool} />

      <HomeBrowseTaxonomy />
      <HomeForFans />
      <HomeLegacyCta />

      <Suspense fallback={<BlogFallback />}>
        <HomeBlogTeaser />
      </Suspense>
    </main>
  );
}
