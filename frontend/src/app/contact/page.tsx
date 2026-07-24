import type { Metadata } from "next";
import Link from "next/link";

import {
  PublicCtaPair,
  PublicPageShell,
} from "@/components/marketing/PublicPageShell";
import { brand } from "@/lib/brand";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = buildPageMetadata({
  title: "Contact",
  description: `Contact ${brand.name} Support — tickets, payments, hosts, and platform help.`,
  path: "/contact",
});

const channels = [
  {
    title: "Support tickets",
    body: "Best for order issues, refunds, account help, and host ops questions.",
    href: "/support/new",
    cta: "Open a ticket",
  },
  {
    title: "Track a request",
    body: "Already contacted us? Look up your ticket with your email and reference.",
    href: "/support/tickets/lookup",
    cta: "Track ticket",
  },
  {
    title: "Report abuse",
    body: "Report harmful content, harassment, or safety concerns for review.",
    href: "/report",
    cta: "Report an issue",
  },
];

export default function ContactPage() {
  return (
    <PublicPageShell
      title="We’re here when something blocks the door"
      description={`Reach the ${brand.name} team through Support Center. Messages become tracked tickets so fans and hosts get clear follow-up.`}
      actions={
        <PublicCtaPair
          primaryHref="/support/new"
          primaryLabel="Contact support"
          secondaryHref="/faq"
          secondaryLabel="Read FAQ"
        />
      }
    >
      <div className="mx-auto grid max-w-4xl gap-5 sm:grid-cols-3">
        {channels.map((c) => (
          <section
            key={c.title}
            className="flex flex-col rounded-[var(--radius-lg)] border border-border bg-card p-5 dark:bg-surface-elevated"
          >
            <h2 className="font-display text-lg font-extrabold text-heading">
              {c.title}
            </h2>
            <p className="mt-2 flex-1 text-sm leading-relaxed text-muted-foreground">
              {c.body}
            </p>
            <Link
              href={c.href}
              className="mt-4 text-sm font-semibold text-primary hover:underline"
            >
              {c.cta} →
            </Link>
          </section>
        ))}
      </div>
      <p className="mx-auto mt-10 max-w-xl text-center text-sm text-muted-foreground">
        For press or partnership intros, open a ticket under Sponsorship or
        Other and we&apos;ll route it.
      </p>
    </PublicPageShell>
  );
}
