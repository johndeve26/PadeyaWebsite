import { cn } from "@/lib/cn";

import { MarketingSection } from "@/components/marketing/MarketingSection";

import { forHostsToolCategories } from "./content";

export function HostsToolsSection() {
  return (
    <MarketingSection
      id="host-tools"
      tone="dark"
      eyebrow="Host tools"
      title="Everything from listing to legacy"
      description="Five pillars — Event Studio, the door, audience, growth monetization, and ops — not a feature dump."
    >
      <ul className="grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
        {forHostsToolCategories.map((cat, i) => (
          <li
            key={cat.title}
            className={cn(
              "flex flex-col rounded-[var(--radius-xl)] border border-paper/12 bg-paper/[0.04] p-6 sm:p-7",
              i === forHostsToolCategories.length - 1 &&
                "lg:col-span-2 xl:col-span-1",
            )}
          >
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">
              {String(i + 1).padStart(2, "0")}
            </p>
            <h3 className="mt-3 text-xl font-extrabold tracking-tight text-paper sm:text-2xl">
              {cat.title}
            </h3>
            <p className="mt-3 flex-1 text-base leading-relaxed text-paper/70">
              {cat.body}
            </p>
            <ul className="mt-5 flex flex-wrap gap-2">
              {cat.items.map((label) => (
                <li
                  key={label}
                  className="rounded-md border border-paper/15 bg-ink/40 px-2.5 py-1 text-xs font-semibold text-paper/80 sm:text-sm"
                >
                  {label}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </MarketingSection>
  );
}
