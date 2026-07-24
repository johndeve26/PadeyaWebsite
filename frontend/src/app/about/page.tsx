import type { Metadata } from "next";
import Link from "next/link";

import {
  PublicCtaPair,
  PublicPageShell,
} from "@/components/marketing/PublicPageShell";
import { brand } from "@/lib/brand";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "About",
  description: `About ${brand.name}: the event marketplace for discovery, verified tickets, Host Legacy, Fan Passport, and growth tools.`,
  path: "/about",
});

export const revalidate = 3600;

const pillars = [
  {
    title: "Discover & attend",
    body: "Fans find events by place and vibe, buy verified tickets, and check in with QR — then keep proof on Fan Passport.",
  },
  {
    title: "Host the night",
    body: "Creators run Event Studio, door check-in, audience CRM, merch, ambassadors, sponsorships, and public Legacy Pages.",
  },
  {
    title: "Stay accountable",
    body: "Verified reviews, Support Center, abuse reporting, and privacy controls keep the marketplace safer for everyone.",
  },
];

const stack = [
  "Event discovery & SEO hubs",
  "Ticketing + QR check-in",
  "Fan Passport & Fan Connect",
  "Host Legacy Pages",
  "Merch & Vault drops",
  "Ambassadors & sponsorships",
  "Support Center",
] as const;

export default function AboutPage() {
  return (
    <PublicPageShell
      title="The marketplace for nights that matter"
      description={`${brand.name} connects fans and hosts around real events — with ticketing, reputation, and growth tools designed for Nigeria’s nightlife and culture scenes, and ready to scale.`}
      actions={
        <PublicCtaPair
          primaryHref="/events"
          primaryLabel="Explore events"
          secondaryHref="/host/onboarding"
          secondaryLabel="Become a host"
        />
      }
    >
      <div className="mx-auto grid max-w-5xl gap-6 sm:grid-cols-3">
        {pillars.map((p) => (
          <section key={p.title} className="space-y-2">
            <h2 className="font-display text-xl font-extrabold text-heading">
              {p.title}
            </h2>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {p.body}
            </p>
          </section>
        ))}
      </div>

      <section className="mx-auto mt-14 max-w-3xl">
        <h2 className="text-center font-display text-2xl font-extrabold text-heading">
          What’s on the platform
        </h2>
        <ul className="mt-6 grid gap-2 sm:grid-cols-2">
          {stack.map((item) => (
            <li
              key={item}
              className="rounded-[var(--radius-md)] border border-border bg-card px-4 py-3 text-sm font-semibold text-foreground dark:bg-surface-elevated"
            >
              {item}
            </li>
          ))}
        </ul>
      </section>

      <section className="mx-auto mt-14 max-w-3xl rounded-[var(--radius-lg)] border border-border bg-ink p-8 text-paper sm:p-10">
        <h2 className="font-display text-2xl font-extrabold tracking-tight">
          Our standard
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-paper/75 sm:text-base">
          Safety, clarity, and accountability matter on the door and in the
          feed. We design for verified access, fair host payouts, and privacy —
          without diluting the energy that makes a night unforgettable.
        </p>
        <p className="mt-4 text-sm text-paper/60">
          Read our{" "}
          <Link href="/community-guidelines" className="text-primary underline">
            Community Guidelines
          </Link>{" "}
          and{" "}
          <Link href="/safety" className="text-primary underline">
            Safety Center
          </Link>
          .
        </p>
      </section>
    </PublicPageShell>
  );
}
