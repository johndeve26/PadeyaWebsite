import Link from "next/link";

import { HomeCardCarousel } from "@/components/home/HomeCardCarousel";
import { Button, Container, SectionHeader } from "@/components/ui";
import { cn } from "@/lib/cn";

const FAN_PILLARS = [
  {
    mark: "01",
    title: "Fan Passport",
    body: "Public-safe identity, badges, attended events, reviews, and privacy controls.",
    href: "/fans",
  },
  {
    mark: "02",
    title: "Fan Connect",
    body: "Meet people around shared events, interests, and nearby scenes — with controls you own.",
    href: "/connect",
  },
  {
    mark: "03",
    title: "Ambassador Rewards",
    body: "Share events you love and earn when approved campaigns are active.",
    href: "/ambassadors",
  },
] as const;

export function HomeForFans() {
  return (
    <section className="relative overflow-hidden bg-ink py-10 text-paper sm:py-12">
      <div
        aria-hidden
        className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-90"
      />
      <Container className="relative min-w-0 space-y-6">
        <SectionHeader
          variant="display"
          tone="dark"
          eyebrow="For explorers"
          title="Find the moment. Keep the proof. Join the scene."
          description="Discover verified events, save your tickets, build your Fan Passport, and connect with people around the events you attend."
        />

        <HomeCardCarousel
          label="For explorers"
          tone="dark"
          until="lg"
          desktopGridClassName="lg:grid-cols-3"
          slideClassName="w-[min(84vw,18.5rem)] sm:w-[min(44vw,20rem)]"
        >
          {FAN_PILLARS.map((item) => (
            <Link
              key={item.title}
              href={item.href}
              className={cn(
                "group relative flex h-full min-h-[10rem] flex-col overflow-hidden rounded-[var(--radius-xl)]",
                "border border-paper/14 bg-paper/[0.045] p-5",
                "shadow-[var(--shadow-glow)] transition duration-200",
                "hover:-translate-y-0.5 hover:border-primary/45 hover:bg-paper/[0.07]",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
              )}
            >
              <span
                aria-hidden
                className="pointer-events-none absolute -right-6 -top-8 h-28 w-28 rounded-full bg-primary/15 blur-2xl transition group-hover:bg-primary/25"
              />
              <span className="relative text-[11px] font-extrabold uppercase tracking-[0.18em] text-primary">
                {item.mark}
              </span>
              <p className="relative mt-3 text-xl font-extrabold tracking-tight text-paper">
                {item.title}
              </p>
              <p className="relative mt-2 flex-1 text-sm leading-relaxed text-paper/70">
                {item.body}
              </p>
            </Link>
          ))}
        </HomeCardCarousel>

        <div className="flex min-w-0 flex-col gap-3 border-t border-paper/10 pt-5 sm:flex-row sm:flex-wrap sm:items-center">
          <Link href="/events" className="w-full sm:w-auto">
            <Button size="lg" className="w-full sm:w-auto">
              Explore events
            </Button>
          </Link>
          <Link
            href="/register?next=/dashboard/passport"
            className="w-full sm:w-auto"
          >
            <Button size="lg" variant="outline-dark" className="w-full sm:w-auto">
              Create Fan Passport
            </Button>
          </Link>
          <Link
            href="/for-fans"
            className="text-sm font-semibold text-paper/65 underline-offset-4 transition hover:text-primary hover:underline sm:ml-1"
          >
            Fan tools overview →
          </Link>
        </div>
      </Container>
    </section>
  );
}
