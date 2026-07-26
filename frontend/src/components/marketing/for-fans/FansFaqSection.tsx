import Link from "next/link";

import { MarketingFaq } from "@/components/marketing/MarketingFaq";
import { MarketingSection } from "@/components/marketing/MarketingSection";

import { forFansFaqs } from "./content";

export function FansFaqSection() {
  return (
    <MarketingSection
      eyebrow="FAQ"
      title="Questions fans ask first"
      description="Tickets, Passport, Connect, refunds, and Support, answered clearly."
    >
      <MarketingFaq items={forFansFaqs} />
      <p className="text-sm leading-relaxed text-muted-foreground">
        More help in the{" "}
        <Link
          href="/faq"
          className="font-semibold text-primary-text hover:underline"
        >
          FAQ
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
