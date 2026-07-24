import type { Metadata } from "next";

import {
  PublicCtaPair,
  PublicPageShell,
} from "@/components/marketing/PublicPageShell";
import {
  BuyerFeesSection,
  FeeCategoriesSection,
  HighVolumeSection,
  HostEarningsSection,
  PricingBottomCtas,
  PricingFaqSection,
  PricingPlatformRelationship,
  PricingTier,
} from "@/components/pricing/PricingSections";
import { brand } from "@/lib/brand";
import { FALLBACK_FEE_CATEGORIES } from "@/lib/legal/pricing-content";
import { fetchPublicPricing } from "@/lib/pricing-api";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Pricing",
  description: `How ${brand.name} pricing works for fans and hosts — free to join, configurable platform fees on sales, clear checkout totals before you pay.`,
  path: "/pricing",
});

export const revalidate = 3600;

export default async function PricingPage() {
  const pricing = await fetchPublicPricing();
  const categories = pricing?.categories?.length
    ? pricing.categories
    : FALLBACK_FEE_CATEGORIES;

  return (
    <PublicPageShell
      title="Simple pricing for a serious night"
      description={`Fans use ${brand.name} free. Hosts pay platform fees when sales succeed — configurable by admin, and they may differ by host. Checkout always shows your final total before you pay.`}
      actions={
        <PublicCtaPair
          primaryHref="/host/onboarding"
          primaryLabel="Become a host"
          secondaryHref="/events"
          secondaryLabel="Explore events"
        />
      }
    >
      <div className="space-y-14 sm:space-y-16">
        <PricingTier />

        <BuyerFeesSection />

        <HostEarningsSection />

        <FeeCategoriesSection
          categories={categories}
          note={pricing?.note ?? null}
        />

        <HighVolumeSection />

        <div data-testid="platform-relationship-section">
          <PricingPlatformRelationship />
        </div>

        <PricingFaqSection />

        <PricingBottomCtas />
      </div>
    </PublicPageShell>
  );
}
