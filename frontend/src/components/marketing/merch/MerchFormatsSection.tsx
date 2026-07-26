import { MarketingFeatureGrid } from "@/components/marketing/MarketingFeatureGrid";
import { MarketingSection } from "@/components/marketing/MarketingSection";

import { merchFormats } from "./content";

export function MerchFormatsSection() {
  return (
    <MarketingSection
      id="formats"
      tone="dark"
      eyebrow="Merch formats"
      title="Five ways merch works on Pàdéyá"
      description="Event add-ons, standalone products, post-event drops, Vault exclusives, and pickup or fulfillment. Pick what fits the night."
    >
      <MarketingFeatureGrid
        items={merchFormats}
        columns={3}
        tone="dark"
        density="pillars"
      />
    </MarketingSection>
  );
}
