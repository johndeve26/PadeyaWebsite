import Link from "next/link";

import { HomeCardCarousel } from "@/components/home/HomeCardCarousel";
import { Button, Container, SectionHeader } from "@/components/ui";
import { cn } from "@/lib/cn";

const HOST_FEATURES = [
  {
    mark: "01",
    title: "Create & sell",
    body: "Event Studio, ticket tiers, capacity, and listings ready for discovery.",
  },
  {
    mark: "02",
    title: "QR check-in",
    body: "Door scanning for staff — including offline-friendly foundations for busy nights.",
  },
  {
    mark: "03",
    title: "Audience CRM",
    body: "Followers, segments, and announcements after the lights come up.",
  },
  {
    mark: "04",
    title: "Merch Studio",
    body: "Sell event merch alongside tickets and manage pickup fulfillment.",
  },
  {
    mark: "05",
    title: "Ambassadors",
    body: "Launch referral campaigns that move inventory with tracked conversions.",
  },
  {
    mark: "06",
    title: "Legacy Page",
    body: "A public host profile with history, reviews, Vault, and upcoming nights.",
  },
] as const;

export function HomeForHosts() {
  return (
    <section className="relative overflow-hidden border-t border-paper/10 bg-ink py-10 text-paper sm:py-12">
      <div
        aria-hidden
        className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-70"
      />
      <Container className="relative min-w-0 space-y-6">
        <SectionHeader
          variant="display"
          tone="dark"
          eyebrow="For hosts"
          title="Run the night end to end."
          description="Create events, sell tickets, check guests in, grow your audience, and leave a Legacy that outlasts one flyer."
        />

        <HomeCardCarousel
          label="Host tools"
          tone="dark"
          until="lg"
          desktopGridClassName="lg:grid-cols-3"
          slideClassName="w-[min(84vw,18.5rem)] sm:w-[min(44vw,20rem)]"
        >
          {HOST_FEATURES.map((tool) => (
            <div
              key={tool.title}
              className={cn(
                "group relative flex h-full min-h-[9.5rem] flex-col overflow-hidden rounded-[var(--radius-xl)]",
                "border border-paper/14 bg-paper/[0.045] p-5",
                "transition duration-200 hover:border-primary/40 hover:bg-paper/[0.07]",
              )}
            >
              <span
                aria-hidden
                className="pointer-events-none absolute -right-8 -top-10 h-24 w-24 rounded-full bg-primary/12 blur-2xl transition group-hover:bg-primary/20"
              />
              <span className="relative text-[11px] font-extrabold uppercase tracking-[0.18em] text-primary">
                {tool.mark}
              </span>
              <p className="relative mt-3 text-lg font-extrabold tracking-tight text-paper">
                {tool.title}
              </p>
              <p className="relative mt-2 flex-1 text-sm leading-relaxed text-paper/70">
                {tool.body}
              </p>
            </div>
          ))}
        </HomeCardCarousel>

        <div className="flex min-w-0 flex-col gap-3 border-t border-paper/10 pt-5 sm:flex-row sm:flex-wrap sm:items-center">
          <Link href="/host/events/new" className="w-full sm:w-auto">
            <Button size="lg" className="w-full sm:w-auto">
              Create event
            </Button>
          </Link>
          <Link href="/register?next=/host" className="w-full sm:w-auto">
            <Button size="lg" variant="outline-dark" className="w-full sm:w-auto">
              Become a host
            </Button>
          </Link>
          <Link
            href="/for-hosts"
            className="text-sm font-semibold text-paper/65 underline-offset-4 transition hover:text-primary hover:underline sm:ml-1"
          >
            Host tools overview →
          </Link>
        </div>
      </Container>
    </section>
  );
}
