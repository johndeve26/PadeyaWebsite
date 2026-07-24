import Link from "next/link";

import { MarketingFeatureGrid } from "@/components/marketing/MarketingFeatureGrid";
import { MarketingSection } from "@/components/marketing/MarketingSection";
import { Button } from "@/components/ui";

import { forFansRewards } from "./content";

export function FansRewardsSection() {
  return (
    <MarketingSection
      tone="muted"
      eyebrow="Ambassadors & rewards"
      title="Share the night. Earn when campaigns are open."
      description="Promote nights you love with tracked links. Rewards attach only to verified paid sales — honest about what hosts enable."
      headerAction={
        <Link href="/ambassadors" className="hidden sm:inline-flex">
          <Button variant="secondary" size="lg">
            Learn Ambassadors
          </Button>
        </Link>
      }
    >
      <MarketingFeatureGrid
        items={forFansRewards}
        columns={3}
        density="pillars"
      />
    </MarketingSection>
  );
}
