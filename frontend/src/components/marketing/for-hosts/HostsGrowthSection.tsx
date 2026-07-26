import Link from "next/link";

import { MarketingSection } from "@/components/marketing/MarketingSection";
import { Media } from "@/components/ui";

import { forHostsGrowth } from "./content";

export function HostsGrowthSection() {
  return (
    <MarketingSection
      tone="ink-soft"
      eyebrow="Growth after the night"
      title="Tools that compound after one night"
      description="Ambassadors, sponsorships, CRM, Legacy, Vault, and merch, so the next event starts warmer."
    >
      <div className="mb-8 grid gap-3 sm:grid-cols-3">
        {[
          {
            src: "/demo/events/mainland-vibes-2025.svg",
            label: "Event nights",
          },
          {
            src: "/demo/vault/vip-gallery.svg",
            label: "Vault drops",
          },
          {
            src: "/demo/hosts/djmaze-cover.svg",
            label: "Host presence",
          },
        ].map((tile) => (
          <div
            key={tile.label}
            className="relative aspect-[16/10] overflow-hidden rounded-[var(--radius-lg)] border border-paper/12 bg-ink"
          >
            <Media
              src={tile.src}
              alt=""
              className="absolute inset-0 h-full w-full object-cover opacity-90"
            />
            <div
              aria-hidden
              className="absolute inset-0 bg-gradient-to-t from-ink/80 via-transparent to-transparent"
            />
            <span className="absolute bottom-3 left-3 text-sm font-extrabold text-paper">
              {tile.label}
            </span>
          </div>
        ))}
      </div>
      <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {forHostsGrowth.map((item) => (
          <li
            key={item.title}
            className="flex flex-col rounded-[var(--radius-xl)] border border-paper/14 bg-paper/[0.06] p-6 sm:p-7"
          >
            <h3 className="text-xl font-extrabold tracking-tight text-paper">
              {item.title}
            </h3>
            <p className="mt-3 flex-1 text-base leading-relaxed text-paper/70">
              {item.body}
            </p>
            {item.href && item.linkLabel ? (
              <Link
                href={item.href}
                className="mt-5 text-sm font-semibold text-primary hover:underline"
              >
                {item.linkLabel} →
              </Link>
            ) : null}
          </li>
        ))}
      </ul>
    </MarketingSection>
  );
}
