import Link from "next/link";

import { MarketingSection } from "@/components/marketing/MarketingSection";

import { forHostsFees } from "./content";

export function HostsPricingSection() {
  return (
    <MarketingSection
      eyebrow="Pricing"
      title={forHostsFees.title}
      description={forHostsFees.body}
    >
      <div className="flex flex-col gap-5 overflow-hidden rounded-[var(--radius-xl)] border border-border bg-gradient-to-br from-card via-card to-[color-mix(in_srgb,var(--primary)_8%,var(--card))] p-6 shadow-[var(--shadow-soft)] dark:from-surface-elevated dark:via-surface-elevated dark:to-[color-mix(in_srgb,var(--primary)_12%,var(--surface-elevated))] sm:flex-row sm:items-center sm:justify-between sm:gap-8 sm:p-8 md:p-10">
        <div className="max-w-xl space-y-2">
          <p className="text-xl font-extrabold tracking-tight text-heading sm:text-2xl">
            {forHostsFees.lead}
          </p>
          <p className="text-sm leading-relaxed text-muted-foreground sm:text-base">
            See how host fees work, what fans get free, and when to talk about
            volume pricing on the live Pricing page.
          </p>
        </div>
        <Link
          href={forHostsFees.cta.href}
          className="inline-flex shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-primary px-5 py-3 text-sm font-extrabold text-ink transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring sm:text-base"
        >
          {forHostsFees.cta.label}
        </Link>
      </div>
    </MarketingSection>
  );
}
