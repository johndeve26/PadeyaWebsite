"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { EligibleEventsGrid } from "@/components/ambassadors/EligibleEventsGrid";
import { headerDarkSurfaceProps } from "@/components/layout/headerSurface";
import { Button, Container, SkeletonLoader } from "@/components/ui";
import { fetchDomainEligibleEvents } from "@/lib/ambassadors-api";
import { brand } from "@/lib/brand";
import { fetchEligibleAmbassadorEvents } from "@/lib/promos-api";
import type { EligibleAmbassadorEvent } from "@/lib/types/promos";

const FAQ = [
  {
    q: "Who can become an Ambassador?",
    a: "Any active Pàdéyá account that accepts Ambassador terms can join open Event Ambassador campaigns. You do not need a host account.",
  },
  {
    q: "When do I earn commission?",
    a: "Only after a referred purchase is verified paid. Pending or failed checkouts never create earnings. Refunds reverse commission.",
  },
  {
    q: "What do Ambassadors get access to?",
    a: "Your link, code, clicks, confirmed sales totals, and earnings status. You never get host dashboard, scanner, buyer private data, or attendee lists.",
  },
  {
    q: "How do rewards work?",
    a: "Campaigns may pay percentage or flat commission, reward-only perks, free tickets after a sales threshold, or leaderboard prizes — set by the host.",
  },
  {
    q: "How do I get paid?",
    a: "Earnings move from estimated → approved → payable → paid. Hold periods may apply before approval. Payout rails appear in your Ambassadors dashboard when available.",
  },
] as const;

export default function AmbassadorsLandingPage() {
  const [events, setEvents] = useState<EligibleAmbassadorEvent[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const domain = await fetchDomainEligibleEvents();
        if (active && domain.length > 0) {
          setEvents(
            domain.map((e) => ({
              id: e.id,
              title: e.title,
              slug: e.slug,
              city: e.city,
              start_datetime: e.start_datetime,
              banner_url: e.banner_url,
              host_display_name: e.host_display_name,
              open_ambassador_commission_percent: e.commission_value,
              open_ambassadors_enabled: true,
            })),
          );
          return;
        }
        const legacy = await fetchEligibleAmbassadorEvents();
        if (active) setEvents(legacy);
      } catch {
        try {
          const legacy = await fetchEligibleAmbassadorEvents();
          if (active) setEvents(legacy);
        } catch {
          if (active) setEvents([]);
        }
      } finally {
        if (active) setLoaded(true);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="min-w-0">
      <section
        {...headerDarkSurfaceProps}
        className="relative overflow-hidden border-b border-ink bg-ink text-paper"
      >
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            backgroundImage: `url(${brand.heroImage})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
          aria-hidden
        />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-ink/70 via-ink/85 to-ink" aria-hidden />
        <Container className="relative py-16 sm:py-24">
          <Image
            src={brand.logos.dark}
            alt={brand.name}
            width={160}
            height={40}
            className="h-9 w-auto"
            priority
          />
          <h1 className="mt-8 max-w-2xl text-4xl font-extrabold tracking-tight sm:text-5xl">
            Pàdéyá Ambassadors
          </h1>
          <p className="mt-4 max-w-xl text-base text-subtle-foreground sm:text-lg">
            Promote events you love. Share your link. Earn on verified ticket and
            merch sales — never from a fake frontend “success” screen.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/ambassadors/events">
              <Button size="lg">Start promoting</Button>
            </Link>
            <Link href="/ambassadors/how-it-works">
              <Button size="lg" variant="outline-dark">
                How it works
              </Button>
            </Link>
            <Link href="/dashboard/ambassador">
              <Button
                size="lg"
                variant="ghost"
                className="text-paper hover:bg-paper/10"
              >
                My dashboard
              </Button>
            </Link>
          </div>
        </Container>
      </section>

      <Container className="space-y-16 py-12 sm:py-16">
        <section className="space-y-6">
          <div>
            <h2 className="text-2xl font-extrabold text-heading">How it works</h2>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              Three steps from join to earnings — Ambassadors stay separate from host
              team and scanner access.
            </p>
          </div>
          <div className="grid gap-8 md:grid-cols-3">
            {[
              {
                step: "01",
                title: "Join an open event",
                body: "Accept terms on an eligible event and get a unique Ambassador link and code instantly.",
              },
              {
                step: "02",
                title: "Share your link",
                body: "Post your link, code, or QR. We track clicks and last-click attribution for the campaign window.",
              },
              {
                step: "03",
                title: "Earn on verified sales",
                body: "When a referred order is paid and verified, commission or rewards are attributed to you.",
              },
            ].map((item) => (
              <div key={item.step}>
                <p className="text-[11px] font-extrabold uppercase tracking-[0.18em] text-accent">
                  {item.step}
                </p>
                <h3 className="mt-2 text-lg font-extrabold text-heading">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm text-body">{item.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-4 border-y border-border py-10">
          <h2 className="text-2xl font-extrabold text-heading">
            Earnings & rewards
          </h2>
          <p className="max-w-2xl text-sm text-body">
            Hosts set the rules per campaign: percentage of sales, flat per ticket or
            merch order, reward-only perks, free tickets after a sales streak, or
            leaderboard prizes. You see estimated, approved, and payable balances in
            your dashboard. Hold periods may apply before payout approval.
          </p>
          <Link href="/ambassadors/events">
            <Button size="sm">Start promoting</Button>
          </Link>
        </section>

        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-2xl font-extrabold text-heading">
                Eligible events
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Open Ambassadors campaigns you can join today.
              </p>
            </div>
            <Link href="/ambassadors/events">
              <Button size="sm" variant="secondary">
                See all
              </Button>
            </Link>
          </div>
          {!loaded ? (
            <SkeletonLoader lines={4} />
          ) : (
            <EligibleEventsGrid events={events.slice(0, 6)} />
          )}
        </section>

        <section className="space-y-6">
          <h2 className="text-2xl font-extrabold text-heading">FAQ</h2>
          <div className="space-y-4">
            {FAQ.map((item) => (
              <details
                key={item.q}
                className="group border-b border-border pb-4"
              >
                <summary className="cursor-pointer list-none text-base font-bold text-heading marker:content-none [&::-webkit-details-marker]:hidden">
                  <span className="flex items-center justify-between gap-3">
                    {item.q}
                    <span className="text-muted-foreground transition group-open:rotate-45">
                      +
                    </span>
                  </span>
                </summary>
                <p className="mt-2 max-w-2xl text-sm text-body">{item.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="rounded-[var(--radius-xl)] bg-ink px-6 py-10 text-paper sm:px-10">
          <h2 className="text-2xl font-extrabold">Ready to promote?</h2>
          <p className="mt-2 max-w-lg text-sm text-subtle-foreground">
            Pick an eligible event, join Ambassadors, and share your link.
          </p>
          <div className="mt-6">
            <Link href="/ambassadors/events">
              <Button size="lg">Start promoting</Button>
            </Link>
          </div>
        </section>
      </Container>
    </main>
  );
}
