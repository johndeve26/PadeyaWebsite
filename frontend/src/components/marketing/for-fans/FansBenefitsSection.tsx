import Link from "next/link";

import { MarketingFeatureGrid } from "@/components/marketing/MarketingFeatureGrid";
import { MarketingSection } from "@/components/marketing/MarketingSection";
import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";

import { forFansBenefits, forFansPillars } from "./content";

export function FansBenefitsSection() {
  return (
    <MarketingSection
      animate
      eyebrow="For fans"
      title="Find the moment. Keep the proof. Join the scene."
      description="Discover verified events, save your tickets, build your Fan Passport, and connect with people around the nights you attend."
    >
      <ul className="grid auto-rows-fr gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3">
        {forFansPillars.map((item, index) => (
          <li key={item.title} className="min-w-0">
            <Link
              href={item.href || "/for-fans"}
              className={cn(
                "group relative flex h-full min-h-[11.5rem] flex-col overflow-hidden rounded-[var(--radius-xl)]",
                "border border-border/90 bg-gradient-to-br from-card via-card to-surface-muted p-5 sm:p-6",
                "shadow-[var(--shadow-soft)] transition duration-200",
                "hover:-translate-y-0.5 hover:border-primary/45 hover:shadow-[var(--shadow-glow)]",
                "dark:border-paper/12 dark:from-surface-elevated dark:via-surface-elevated dark:to-surface-inset",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
              )}
            >
              <span
                aria-hidden
                className="pointer-events-none absolute -right-6 -top-8 h-28 w-28 rounded-full bg-primary/15 blur-2xl transition group-hover:bg-primary/25"
              />
              <span className="relative text-[11px] font-extrabold uppercase tracking-[0.18em] text-primary">
                {String(index + 1).padStart(2, "0")}
              </span>
              <p className="relative mt-3 text-xl font-extrabold tracking-tight text-heading sm:text-2xl">
                {item.title}
              </p>
              <p className="relative mt-2.5 flex-1 text-sm leading-relaxed text-muted-foreground sm:text-base">
                {item.body}
              </p>
            </Link>
          </li>
        ))}
      </ul>

      <div className="space-y-4">
        <p className="text-xs font-extrabold uppercase tracking-[0.16em] text-muted-foreground">
          The fan journey
        </p>
        <MarketingFeatureGrid
          items={forFansBenefits}
          columns={5}
          density="pillars"
        />
      </div>

      <div className="flex flex-col gap-3 border-t border-border pt-6 sm:flex-row sm:flex-wrap sm:items-center dark:border-border">
        <Link href="/events" className="w-full sm:w-auto">
          <Button size="lg" className="w-full sm:w-auto">
            Explore events
          </Button>
        </Link>
        <Link
          href="/register?next=/dashboard/passport"
          className="w-full sm:w-auto"
        >
          <Button size="lg" variant="secondary" className="w-full sm:w-auto">
            Create Fan Passport
          </Button>
        </Link>
      </div>
    </MarketingSection>
  );
}
