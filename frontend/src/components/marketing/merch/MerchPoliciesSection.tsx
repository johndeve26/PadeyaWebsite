import Link from "next/link";

import { MarketingFeatureGrid } from "@/components/marketing/MarketingFeatureGrid";
import { MarketingSection } from "@/components/marketing/MarketingSection";

import { merchPoliciesPoints } from "./content";

export function MerchPoliciesSection() {
  return (
    <MarketingSection
      id="policies"
      tone="muted"
      eyebrow="Policies and support"
      title="Hosts fulfill. Pàdéyá powers the rails."
      description="Product accuracy, pickup, and availability sit with the host. Refunds follow policy and host rules — Support and Help are here when you need them."
    >
      <MarketingFeatureGrid items={merchPoliciesPoints} columns={2} />
      <p className="text-sm leading-relaxed text-muted-foreground">
        <Link
          href="/refund-policy"
          className="font-semibold text-primary-text hover:underline"
        >
          Refund Policy
        </Link>
        {" · "}
        <Link
          href="/ticket-policy"
          className="font-semibold text-primary-text hover:underline"
        >
          Ticket Policy
        </Link>
        {" · "}
        <Link
          href="/support"
          className="font-semibold text-primary-text hover:underline"
        >
          Support
        </Link>
        {" · "}
        <Link
          href="/help"
          className="font-semibold text-primary-text hover:underline"
        >
          Help Center
        </Link>
        .
      </p>
    </MarketingSection>
  );
}
