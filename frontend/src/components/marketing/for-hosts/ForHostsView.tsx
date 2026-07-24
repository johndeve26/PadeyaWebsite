import Link from "next/link";

import { MarketingAudienceHero } from "@/components/marketing/MarketingAudienceHero";
import { MarketingFinalCta } from "@/components/marketing/MarketingFinalCta";

import { HostsAudiencesSection } from "./HostsAudiencesSection";
import { HostsFaqSection } from "./HostsFaqSection";
import { HostsGrowthSection } from "./HostsGrowthSection";
import { HostsPricingSection } from "./HostsPricingSection";
import { HostsTicketingSection } from "./HostsTicketingSection";
import { HostsToolsSection } from "./HostsToolsSection";
import { HostsWorkflowSection } from "./HostsWorkflowSection";
import { forHostsFinalCta, forHostsHero } from "./content";

export function ForHostsView() {
  return (
    <main className="min-w-0 overflow-x-clip pb-2">
      <MarketingAudienceHero
        eyebrow={forHostsHero.eyebrow}
        headline={forHostsHero.headline}
        support={forHostsHero.support}
        trustLine={forHostsHero.trustLine}
        primary={forHostsHero.primary}
        secondary={forHostsHero.secondary}
        tertiary={
          <p className="text-sm text-paper/55">
            Prefer the directory?{" "}
            <Link href="/hosts" className="font-semibold text-primary hover:underline">
              Browse hosts
            </Link>
            {" · "}
            <Link href="/pricing" className="font-semibold text-primary hover:underline">
              Pricing
            </Link>
            {" · "}
            <Link href="/blog" className="font-semibold text-primary hover:underline">
              Blog
            </Link>
            {" · "}
            <Link href="/events" className="font-semibold text-primary hover:underline">
              Events
            </Link>
          </p>
        }
      />

      <HostsAudiencesSection />
      <HostsToolsSection />
      <HostsWorkflowSection />
      <HostsTicketingSection />
      <HostsGrowthSection />
      <HostsPricingSection />
      <HostsFaqSection />

      <MarketingFinalCta
        title={forHostsFinalCta.title}
        description={forHostsFinalCta.description}
        primary={forHostsFinalCta.primary}
        secondary={forHostsFinalCta.secondary}
        tertiary={forHostsFinalCta.tertiary}
      />
    </main>
  );
}
