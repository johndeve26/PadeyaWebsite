import Link from "next/link";

import { MarketingAudienceHero } from "@/components/marketing/MarketingAudienceHero";
import { MarketingFinalCta } from "@/components/marketing/MarketingFinalCta";
import { brand } from "@/lib/brand";

import { FansBenefitsSection } from "./FansBenefitsSection";
import { FansConnectSection } from "./FansConnectSection";
import { FansDiscoverySection } from "./FansDiscoverySection";
import { FansFaqSection } from "./FansFaqSection";
import { FansPassportSection } from "./FansPassportSection";
import { FansRewardsSection } from "./FansRewardsSection";
import { FansTicketingSection } from "./FansTicketingSection";
import { forFansFinalCta, forFansHero } from "./content";

export function ForFansView() {
  return (
    <main className="min-w-0 overflow-x-clip pb-2">
      <MarketingAudienceHero
        eyebrow={forFansHero.eyebrow}
        headline={forFansHero.headline}
        support={forFansHero.support}
        trustLine={forFansHero.trustLine}
        primary={forFansHero.primary}
        secondary={forFansHero.secondary}
        tertiary={
          <p className="text-sm text-paper/55">
            Already on {brand.name}?{" "}
            <Link
              href="/dashboard/passport"
              className="font-semibold text-primary hover:underline"
            >
              Open Fan Passport
            </Link>
            {" · "}
            <Link href="/blog" className="font-semibold text-primary hover:underline">
              Blog
            </Link>
          </p>
        }
      />

      <FansBenefitsSection />
      <FansPassportSection />
      <FansConnectSection />
      <FansTicketingSection />
      <FansDiscoverySection />
      <FansRewardsSection />
      <FansFaqSection />

      <MarketingFinalCta
        title={forFansFinalCta.title}
        description={forFansFinalCta.description}
        primary={forFansFinalCta.primary}
        secondary={forFansFinalCta.secondary}
      />
    </main>
  );
}
