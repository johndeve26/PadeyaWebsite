import Link from "next/link";

import { MarketingFeatureGrid } from "@/components/marketing/MarketingFeatureGrid";
import { MarketingSection } from "@/components/marketing/MarketingSection";

import { merchFansPoints } from "./content";

export function MerchFansSection() {
  return (
    <MarketingSection
      animate
      id="for-fans"
      eyebrow="For fans"
      title="Buy the night’s proof — before, during, and after"
      description="Attach merch to tickets, catch post-event drops, unlock Vault exclusives, and track orders in your dashboard."
    >
      <MarketingFeatureGrid items={merchFansPoints} columns={3} density="pillars" />
      <p className="text-sm leading-relaxed text-muted-foreground">
        Track orders in{" "}
        <Link
          href="/dashboard/merchandise"
          className="font-semibold text-primary-text hover:underline"
        >
          Personal → Merch
        </Link>
        {" · "}
        <Link
          href="/help"
          className="font-semibold text-primary-text hover:underline"
        >
          Help Center
        </Link>
        {" · "}
        <Link
          href="/support"
          className="font-semibold text-primary-text hover:underline"
        >
          Support
        </Link>
        .
      </p>
    </MarketingSection>
  );
}
