import Link from "next/link";

import { MarketingFaq } from "@/components/marketing/MarketingFaq";
import { MarketingSection } from "@/components/marketing/MarketingSection";

import { forHostsFaqs } from "./content";

export function HostsFaqSection() {
  return (
    <MarketingSection
      tone="muted"
      eyebrow="FAQ"
      title="Questions hosts ask first"
      description="Straight answers before you create your first event."
    >
      <MarketingFaq items={forHostsFaqs} />
      <p className="pt-2 text-sm text-muted-foreground sm:text-base">
        More answers on the{" "}
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
          href="/safety"
          className="font-semibold text-primary-text hover:underline"
        >
          Safety Center
        </Link>
        .
      </p>
    </MarketingSection>
  );
}
