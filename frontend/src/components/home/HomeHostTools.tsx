import Link from "next/link";

import { Button, Container, SectionHeader } from "@/components/ui";

const TOOLS = [
  {
    title: "Publish & sell",
    body: "Event pages, ticket tiers, tables, capacity, and SEO-ready listings.",
  },
  {
    title: "Door-ready check-in",
    body: "Staff QR scanning with an offline-friendly foundation for busy doors.",
  },
  {
    title: "Audience CRM",
    body: "Segments, announcements, and follow-up after the night ends.",
  },
  {
    title: "Clear finance",
    body: "Ledger, balances, and payout requests with immutable evidence.",
  },
  {
    title: "Promo codes",
    body: "Campaign codes and ambassadors that actually move inventory.",
  },
  {
    title: "Analytics",
    body: "Sales, funnel, and door metrics hosts can act on, not vanity charts.",
  },
] as const;

export function HomeHostTools() {
  return (
    <section className="relative overflow-hidden bg-ink py-16 text-paper sm:py-20">
      <div aria-hidden className="padeya-hero-glow pointer-events-none absolute inset-0" />
      <Container className="relative space-y-10">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between lg:gap-10">
          <div className="min-w-0 flex-1">
            <SectionHeader
              tone="dark"
              eyebrow="Host tools"
              title="Run the night from first ticket to final check-in."
              description="Create event pages, sell ticket tiers, manage attendees, scan QR tickets, track revenue, and grow your audience after the event."
            />
          </div>
          <div className="flex shrink-0 flex-col gap-3 sm:flex-row sm:flex-wrap lg:pb-1">
            <Link href="/host/onboarding" className="w-full sm:w-auto">
              <Button size="lg" className="w-full sm:w-auto">
                Create event
              </Button>
            </Link>
            <Link href="/hosts" className="w-full sm:w-auto">
              <Button size="lg" variant="outline-dark" className="w-full sm:w-auto">
                Browse hosts
              </Button>
            </Link>
          </div>
        </div>
        <ul className="grid auto-rows-fr gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {TOOLS.map((tool) => (
            <li
              key={tool.title}
              className="flex h-full flex-col rounded-[var(--radius-lg)] border border-paper/12 bg-paper/[0.03] p-5 sm:p-6"
            >
              <p className="text-lg font-extrabold tracking-tight">{tool.title}</p>
              <p className="mt-2.5 flex-1 text-sm leading-relaxed text-subtle-foreground sm:text-base">
                {tool.body}
              </p>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
