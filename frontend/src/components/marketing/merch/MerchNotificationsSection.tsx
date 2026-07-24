import { MarketingFeatureGrid } from "@/components/marketing/MarketingFeatureGrid";
import { MarketingSection } from "@/components/marketing/MarketingSection";

import { merchNotificationsPoints } from "./content";

export function MerchNotificationsSection() {
  return (
    <MarketingSection
      id="notifications"
      tone="muted"
      eyebrow="Notifications"
      title="Alerts when drops land — when settings allow"
      description="Admins control merch notification types. Hosts may notify eligible fans for drops. Your preferences are respected where they apply."
    >
      <MarketingFeatureGrid items={merchNotificationsPoints} columns={2} />
    </MarketingSection>
  );
}
