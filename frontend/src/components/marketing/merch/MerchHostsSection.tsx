import Link from "next/link";

import { MarketingFeatureGrid } from "@/components/marketing/MarketingFeatureGrid";
import { MarketingSection } from "@/components/marketing/MarketingSection";

import { merchHostsPoints } from "./content";

export function MerchHostsSection() {
  return (
    <MarketingSection
      id="for-hosts"
      tone="muted"
      eyebrow="For hosts"
      title="Create, attach, drop, and fulfill from one workspace"
      description="Merch Studio covers products, event links, standalone sales, Vault exclusives, inventory, and pickup."
    >
      <MarketingFeatureGrid items={merchHostsPoints} columns={3} density="pillars" />
      <p className="text-sm leading-relaxed text-muted-foreground">
        Start in{" "}
        <Link
          href="/host/merchandise"
          className="font-semibold text-primary-text hover:underline"
        >
          Merch Studio
        </Link>
        {" · "}
        <Link
          href="/host/events"
          className="font-semibold text-primary-text hover:underline"
        >
          Host events
        </Link>
        {" · "}
        <Link
          href="/for-hosts"
          className="font-semibold text-primary-text hover:underline"
        >
          For hosts
        </Link>
        .
      </p>
    </MarketingSection>
  );
}
