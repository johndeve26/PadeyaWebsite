import { MarketingSection } from "@/components/marketing/MarketingSection";

import { merchWorkflow } from "./content";

export function MerchHowItWorksSection() {
  return (
    <MarketingSection
      id="how-it-works"
      tone="muted"
      eyebrow="How it works"
      title="From Merch Studio to fan dashboard"
      description="Seven steps from product creation to fulfillment tracking."
    >
      <ol className="relative space-y-0">
        {merchWorkflow.map((step, i) => {
          const n = String(i + 1).padStart(2, "0");
          const last = i === merchWorkflow.length - 1;
          return (
            <li
              key={step.id}
              className="relative grid gap-4 pb-8 last:pb-0 sm:grid-cols-[4.5rem_1fr] sm:gap-6 sm:pb-10"
            >
              {!last ? (
                <span
                  aria-hidden
                  className="absolute left-[1.35rem] top-12 hidden h-[calc(100%-2rem)] w-px bg-border sm:block"
                />
              ) : null}
              <div className="flex items-center gap-3 sm:flex-col sm:items-start sm:gap-2">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-2 border-primary bg-card text-sm font-extrabold text-heading shadow-[0_0_0_4px_color-mix(in_srgb,var(--primary)_18%,transparent)] dark:bg-surface-elevated">
                  {n}
                </span>
                {!last ? (
                  <span
                    aria-hidden
                    className="h-px flex-1 bg-border sm:hidden"
                  />
                ) : null}
              </div>
              <div className="min-w-0 rounded-[var(--radius-lg)] border border-border/80 bg-card/70 px-5 py-4 dark:bg-surface-elevated/80 sm:px-6 sm:py-5">
                <h3 className="text-lg font-extrabold tracking-tight text-heading sm:text-xl">
                  {step.label}
                </h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground sm:text-base">
                  {step.description}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </MarketingSection>
  );
}
