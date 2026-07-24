import Link from "next/link";

import { MarketingFeatureGrid } from "@/components/marketing/MarketingFeatureGrid";
import { MarketingSection } from "@/components/marketing/MarketingSection";

import { merchFeesPoints } from "./content";

export function MerchFeesSection() {
  return (
    <MarketingSection
      id="fees"
      eyebrow="Fees and earnings"
      title="Clear totals — no invented percentages"
      description="Merch may carry platform fees or commission. Buyer fees depend on admin settings. Hosts see gross, deductions, and net in finance views."
    >
      <MarketingFeatureGrid items={merchFeesPoints} columns={3} density="pillars" />
      <p className="text-sm leading-relaxed text-muted-foreground">
        Live rates and fee categories live on{" "}
        <Link
          href="/pricing"
          className="font-semibold text-primary-text hover:underline"
        >
          Pricing
        </Link>
        . Hosts review exact deductions in Host → Earnings.
      </p>
    </MarketingSection>
  );
}
