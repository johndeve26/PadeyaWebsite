import { MarketingFeatureGrid } from "@/components/marketing/MarketingFeatureGrid";
import { MarketingSection } from "@/components/marketing/MarketingSection";

import { forFansTicketing } from "./content";

export function FansTicketingSection() {
  return (
    <MarketingSection
      tone="dark"
      eyebrow="Ticketing & safety"
      title="Verified tickets. Credible attendance."
      description="Secure checkout, signed QR check-in, ticket history, and Support when you need a refund path."
    >
      <MarketingFeatureGrid
        items={forFansTicketing}
        tone="dark"
        columns={2}
        density="pillars"
      />
    </MarketingSection>
  );
}
