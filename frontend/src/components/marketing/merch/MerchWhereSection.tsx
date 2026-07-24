import { MarketingFeatureGrid } from "@/components/marketing/MarketingFeatureGrid";
import { MarketingSection } from "@/components/marketing/MarketingSection";

import { merchWherePoints } from "./content";

export function MerchWhereSection() {
  return (
    <MarketingSection
      id="where"
      eyebrow="Where merch appears"
      title="Surfaces fans and hosts already use"
      description="Event pages, checkout, host presence, Vault, drop alerts, fan dashboard, and Merch Studio."
    >
      <MarketingFeatureGrid items={merchWherePoints} columns={3} />
    </MarketingSection>
  );
}
