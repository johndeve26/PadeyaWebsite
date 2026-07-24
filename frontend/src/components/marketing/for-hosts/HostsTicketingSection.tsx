import { MarketingSection } from "@/components/marketing/MarketingSection";

import { forHostsTicketing } from "./content";

export function HostsTicketingSection() {
  return (
    <MarketingSection
      tone="dark"
      eyebrow="Ticketing & check-in"
      title="Secure doors. Credible tickets."
      description="Verified payments before issue, signed QR for staff, and guest entry tools built for real nights."
    >
      <ul className="grid gap-4 sm:grid-cols-2 sm:gap-5">
        {forHostsTicketing.map((item) => (
          <li
            key={item.title}
            className="rounded-[var(--radius-lg)] border border-paper/12 bg-gradient-to-b from-paper/[0.07] to-transparent p-6"
          >
            <div
              aria-hidden
              className="mb-4 h-1 w-8 rounded-full bg-primary"
            />
            <h3 className="text-lg font-extrabold tracking-tight text-paper sm:text-xl">
              {item.title}
            </h3>
            <p className="mt-3 text-sm leading-relaxed text-paper/70 sm:text-[0.95rem]">
              {item.body}
            </p>
          </li>
        ))}
      </ul>
    </MarketingSection>
  );
}
