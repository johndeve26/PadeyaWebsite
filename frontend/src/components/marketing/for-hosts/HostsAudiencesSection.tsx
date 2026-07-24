import { MarketingSection } from "@/components/marketing/MarketingSection";

import { forHostsAudiences } from "./content";

export function HostsAudiencesSection() {
  return (
    <MarketingSection
      animate
      tone="ink-soft"
      eyebrow="Who it is for"
      title="Built for people who put on the night"
      description="Promoters, venues, creators, communities, and brands — Pàdéyá is the workspace between the flyer and the door."
    >
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 sm:gap-5">
        {forHostsAudiences.map((item) => (
          <li
            key={item.title}
            className="group relative overflow-hidden rounded-[var(--radius-xl)] border border-paper/12 bg-paper/[0.05] p-5 sm:p-6"
          >
            <span
              aria-hidden
              className="pointer-events-none absolute -right-6 -top-8 h-24 w-24 rounded-full bg-primary/12 blur-2xl"
            />
            <p className="relative text-lg font-extrabold tracking-tight text-paper sm:text-xl">
              {item.title}
            </p>
            <p className="relative mt-3 text-sm leading-relaxed text-paper/70 sm:text-[0.95rem]">
              {item.body}
            </p>
          </li>
        ))}
      </ul>
    </MarketingSection>
  );
}
