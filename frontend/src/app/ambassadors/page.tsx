"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { EligibleEventsGrid } from "@/components/ambassadors/EligibleEventsGrid";
import { headerDarkSurfaceProps } from "@/components/layout/headerSurface";
import { Badge, Button, Container, SkeletonLoader } from "@/components/ui";
import { track } from "@/lib/analytics";
import { fetchDomainEligibleEvents } from "@/lib/ambassadors-api";
import { brand } from "@/lib/brand";
import {
  fetchEligibleAmbassadorEvents,
  fetchMyReferralPrograms,
  fetchMyReferralSummary,
  type ReferralProgramRow,
  type ReferralSummary,
} from "@/lib/promos-api";
import {
  resolvePublicEnrollmentState,
  type PublicEnrollmentState,
} from "@/lib/ambassador-frontend-alignment";
import type { EligibleAmbassadorEvent } from "@/lib/types/promos";

const FAQ = [
  {
    q: "Who can become an Ambassador?",
    a: "Users may participate in eligible host campaigns or be enrolled in Pàdéyá-wide programs. Availability depends on the active campaign or program — platform-wide enrollment is currently managed by Pàdéyá.",
  },
  {
    q: "What is a Pàdéyá-wide program?",
    a: "A referral program created by Pàdéyá that may cover eligible tickets, merchandise, or both across multiple events. Commission is funded by Pàdéyá.",
  },
  {
    q: "What is a host campaign?",
    a: "A referral campaign created for a specific event by its host. Rules may cover tickets or merchandise and are set for that event.",
  },
  {
    q: "Do I get one referral link?",
    a: "Each enrollment has its own referral link. A combined Pàdéyá-wide program uses one link for the ticket and merchandise rules enabled under that program.",
  },
  {
    q: "Can I join more than one campaign?",
    a: "Yes — you can hold multiple host campaign enrollments and, when enrolled by Pàdéyá, a platform-wide program. All of them appear in one ambassador dashboard.",
  },
  {
    q: "What happens if more than one referral link is used?",
    a: "An eligible matching host event campaign takes priority for that item. A Pàdéyá-wide program may apply when no matching host campaign wins. Each eligible item can produce only one referral commission.",
  },
  {
    q: "Who pays the commission?",
    a: "Pàdéyá funds Pàdéyá-wide program commission. Host event campaign commission follows that campaign’s host-funded rules.",
  },
  {
    q: "When does commission become available?",
    a: "Eligible commission moves through pending, approved, payable, and paid states according to the applicable hold and payout policy. Instant payout is not guaranteed.",
  },
  {
    q: "What happens after a refund?",
    a: "If a referred purchase is fully or partially refunded, the related commission may be adjusted or reversed. Your earnings history continues to show the original earning and any later adjustment.",
  },
  {
    q: "Where can I see my results?",
    a: "In the unified ambassador dashboard — clicks, converted orders, attributed items, commission, and reversals in one place.",
  },
] as const;

export default function AmbassadorsLandingPage() {
  const { user, loading: authLoading, authInitialized } = useAuth();
  const [events, setEvents] = useState<EligibleAmbassadorEvent[]>([]);
  const [eventsLoaded, setEventsLoaded] = useState(false);
  const [summary, setSummary] = useState<ReferralSummary | null>(null);
  const [programs, setPrograms] = useState<ReferralProgramRow[]>([]);
  const [personalLoaded, setPersonalLoaded] = useState(false);
  const [copied, setCopied] = useState(false);

  const signedIn = Boolean(user);
  const isHost = Boolean(
    user?.roles?.some((r) => r === "host" || r === "super_admin"),
  );

  useEffect(() => {
    track("ambassador_page_view", {
      metadata: { auth_state: signedIn ? "signed_in" : "signed_out" },
      dedupeTtlMs: 30_000,
      dedupeScope: "ambassador_page_view",
    });
  }, [signedIn]);

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
        if (active) setEventsLoaded(true);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!authInitialized) return;
    if (!user) {
      setSummary(null);
      setPrograms([]);
      setPersonalLoaded(true);
      return;
    }
    let active = true;
    setPersonalLoaded(false);
    void (async () => {
      try {
        const [s, p] = await Promise.all([
          fetchMyReferralSummary(),
          fetchMyReferralPrograms(),
        ]);
        if (!active) return;
        setSummary(s);
        setPrograms(p);
      } catch {
        if (!active) return;
        // Marketing page must still render; personalized CTA falls back safely.
        setSummary(null);
        setPrograms([]);
      } finally {
        if (active) setPersonalLoaded(true);
      }
    })();
    return () => {
      active = false;
    };
  }, [authInitialized, user]);

  const enrollmentState: PublicEnrollmentState = useMemo(
    () =>
      resolvePublicEnrollmentState(
        signedIn,
        authLoading || !personalLoaded,
        summary,
        programs,
      ),
    [signedIn, authLoading, personalLoaded, summary, programs],
  );

  const ownLink =
    summary?.primary_referral_link_path ||
    programs.find((p) => p.status === "active" && p.referral_link_path)
      ?.referral_link_path ||
    null;

  async function copyOwnLink() {
    if (!ownLink || typeof window === "undefined") return;
    const absolute = new URL(ownLink, window.location.origin).toString();
    try {
      await navigator.clipboard.writeText(absolute);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
      track("ambassador_secondary_cta_click", {
        metadata: {
          auth_state: "signed_in",
          enrollment_state: enrollmentState,
          destination_type: "copy_referral_link",
        },
        dedupeTtlMs: 2_000,
      });
    } catch {
      setCopied(false);
    }
  }

  function trackPrimary(destination: string) {
    track("ambassador_primary_cta_click", {
      metadata: {
        auth_state: signedIn ? "signed_in" : "signed_out",
        enrollment_state: enrollmentState,
        destination_type: destination,
      },
      dedupeTtlMs: 2_000,
    });
  }

  const heroCtas = (() => {
    switch (enrollmentState) {
      case "signed_out":
        return (
          <>
            <Link
              href="/login?next=/ambassadors"
              onClick={() => trackPrimary("sign_in")}
            >
              <Button size="lg">Sign in to continue</Button>
            </Link>
            <a href="#how-it-works">
              <Button size="lg" variant="outline-dark">
                See how it works
              </Button>
            </a>
            <Link href="/register?next=/ambassadors">
              <Button
                size="lg"
                variant="ghost"
                className="text-paper hover:bg-paper/10"
              >
                Create account
              </Button>
            </Link>
          </>
        );
      case "loading":
        return <SkeletonLoader lines={1} className="max-w-md" />;
      case "not_enrolled":
        return (
          <>
            <Link
              href="/dashboard/ambassador"
              onClick={() => trackPrimary("ambassador_area")}
            >
              <Button size="lg">Go to ambassador area</Button>
            </Link>
            <Link href="/ambassadors/events">
              <Button size="lg" variant="outline-dark">
                Browse open host campaigns
              </Button>
            </Link>
            <p className="basis-full text-sm text-subtle-foreground">
              Programs and campaigns appear when you are enrolled or accepted.
              Pàdéyá-wide enrollment is managed by Pàdéyá — not open self-serve.
            </p>
          </>
        );
      case "host_only":
        return (
          <>
            <Link
              href="/dashboard/ambassador"
              onClick={() => trackPrimary("dashboard")}
            >
              <Button size="lg">Open ambassador dashboard</Button>
            </Link>
            <Link href="/dashboard/ambassador">
              <Button size="lg" variant="outline-dark">
                View my campaigns
              </Button>
            </Link>
          </>
        );
      case "platform_only":
        return (
          <>
            <Link
              href="/dashboard/ambassador"
              onClick={() => trackPrimary("dashboard")}
            >
              <Button size="lg">Open ambassador dashboard</Button>
            </Link>
            {ownLink ? (
              <Button size="lg" variant="outline-dark" onClick={() => void copyOwnLink()}>
                {copied ? "Link copied" : "Copy my referral link"}
              </Button>
            ) : null}
          </>
        );
      case "both":
        return (
          <>
            <Link
              href="/dashboard/ambassador"
              onClick={() => trackPrimary("unified_dashboard")}
            >
              <Button size="lg">Open unified dashboard</Button>
            </Link>
            <Link href="/dashboard/ambassador">
              <Button size="lg" variant="outline-dark">
                View my referral links
              </Button>
            </Link>
          </>
        );
      case "inactive":
        return (
          <>
            <p className="basis-full text-sm text-subtle-foreground">
              Your ambassador enrollments are not currently active for new
              earnings. You can still review history in your dashboard.
            </p>
            <Link href="/dashboard/ambassador">
              <Button size="lg" variant="outline-dark">
                Open dashboard history
              </Button>
            </Link>
          </>
        );
      default:
        return null;
    }
  })();

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
        <div
          className="pointer-events-none absolute inset-0 bg-gradient-to-b from-ink/70 via-ink/85 to-ink"
          aria-hidden
        />
        <Container className="relative py-16 sm:py-24">
          <Image
            src={brand.logos.dark}
            alt={brand.name}
            width={160}
            height={40}
            className="h-9 w-auto"
            priority
          />
          <p className="mt-8 text-[11px] font-extrabold uppercase tracking-[0.18em] text-accent">
            Pàdéyá Ambassadors
          </p>
          <h1 className="mt-3 max-w-2xl text-4xl font-extrabold tracking-tight sm:text-5xl">
            Share experiences people will love.
            <span className="block text-accent">Earn from eligible referrals.</span>
          </h1>
          <p className="mt-4 max-w-xl text-base text-subtle-foreground sm:text-lg">
            Join eligible Pàdéyá-wide programs or promote specific campaigns from
            event hosts. Share your referral link and track clicks, referred sales
            and commission from one connected dashboard.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">{heroCtas}</div>
        </Container>
      </section>

      <Container className="space-y-16 py-12 sm:py-16">
        <section
          aria-label="Ambassador features"
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          {[
            "Unique referral links",
            "Ticket and merchandise coverage",
            "Unified tracking",
            "Approved payouts",
          ].map((label) => (
            <div
              key={label}
              className="rounded-[var(--radius-lg)] border border-border bg-surface px-4 py-3 text-sm font-semibold text-foreground"
            >
              {label}
            </div>
          ))}
        </section>

        <section className="space-y-6" aria-labelledby="two-ways-heading">
          <div>
            <h2 id="two-ways-heading" className="text-2xl font-extrabold text-heading">
              Two ways to earn
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              One connected ambassador system — two scopes.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-2">
            <article className="rounded-[var(--radius-xl)] border border-border bg-surface p-6">
              <Badge tone="success">Pàdéyá-wide</Badge>
              <h3 className="mt-3 text-xl font-extrabold text-heading">
                Pàdéyá-wide programs
              </h3>
              <p className="mt-2 text-sm text-body">
                Promote eligible experiences across Pàdéyá with one program link.
                Depending on the program, you may earn from eligible ticket sales,
                merchandise sales, or both.
              </p>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li>One program link</li>
                <li>Eligible events and products</li>
                <li>Commission funded by Pàdéyá</li>
                <li>Invitation or admin enrollment</li>
              </ul>
              {signedIn &&
              (enrollmentState === "platform_only" ||
                enrollmentState === "both") ? (
                <Link
                  href="/dashboard/ambassador"
                  className="mt-5 inline-block"
                  onClick={() =>
                    track("ambassador_scope_card_click", {
                      metadata: { scope: "platform" },
                      dedupeTtlMs: 2_000,
                    })
                  }
                >
                  <Button size="sm">View my programs</Button>
                </Link>
              ) : (
                <p className="mt-5 text-xs text-muted-foreground">
                  Platform-wide access is enrollment-controlled — not open join.
                </p>
              )}
            </article>
            <article className="rounded-[var(--radius-xl)] border border-border bg-surface p-6">
              <Badge tone="neutral">Host campaign</Badge>
              <h3 className="mt-3 text-xl font-extrabold text-heading">
                Host event campaigns
              </h3>
              <p className="mt-2 text-sm text-body">
                Partner with an event host to promote a specific event. Campaign
                rules may cover tickets or merchandise and are set for that event.
              </p>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li>Event-specific</li>
                <li>Ticket or merchandise campaigns</li>
                <li>Host-managed campaign</li>
                <li>Tracked in the same dashboard</li>
              </ul>
              <Link
                href={
                  signedIn &&
                  (enrollmentState === "host_only" || enrollmentState === "both")
                    ? "/dashboard/ambassador"
                    : "/ambassadors/events"
                }
                className="mt-5 inline-block"
                onClick={() =>
                  track("ambassador_scope_card_click", {
                    metadata: { scope: "host" },
                    dedupeTtlMs: 2_000,
                  })
                }
              >
                <Button size="sm" variant="secondary">
                  {signedIn &&
                  (enrollmentState === "host_only" || enrollmentState === "both")
                    ? "View my campaigns"
                    : "Browse open campaigns"}
                </Button>
              </Link>
            </article>
          </div>
        </section>

        <section id="how-it-works" className="space-y-6 scroll-mt-24">
          <div>
            <h2 className="text-2xl font-extrabold text-heading">How it works</h2>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              From enrollment to approved payouts — without host dashboard access.
            </p>
          </div>
          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-5">
            {[
              {
                step: "01",
                title: "Get enrolled",
                body: "Join an eligible host campaign or get enrolled in a Pàdéyá-wide program.",
              },
              {
                step: "02",
                title: "Receive your link",
                body: "Each enrollment provides a unique referral link. A Pàdéyá-wide program uses one link for its enabled ticket and merchandise rules.",
              },
              {
                step: "03",
                title: "Share eligible experiences",
                body: "Share approved events, tickets and products covered by your program or campaign.",
              },
              {
                step: "04",
                title: "Track results",
                body: "View clicks, converted orders, attributed items and commission in your dashboard.",
              },
              {
                step: "05",
                title: "Receive approved payouts",
                body: "Eligible commission progresses through pending, approved, payable and paid states.",
              },
            ].map((item) => (
              <div key={item.step}>
                <p className="text-[11px] font-extrabold uppercase tracking-[0.18em] text-accent">
                  {item.step}
                </p>
                <h3 className="mt-2 text-base font-extrabold text-heading">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm text-body">{item.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-4 rounded-[var(--radius-xl)] border border-border bg-surface p-6 sm:p-8">
          <h2 className="text-2xl font-extrabold text-heading">
            Everything in one ambassador dashboard
          </h2>
          <p className="max-w-2xl text-sm text-body">
            Platform and Host badges, referral links, clicks, converted orders,
            pending and available commission, paid totals, reversals, and ticket
            or merchandise filters — connected in one place.
          </p>
          <div
            className="grid gap-3 sm:grid-cols-3"
            aria-hidden
          >
            {["Platform · Host", "Converted orders", "Commission history"].map(
              (label) => (
                <div
                  key={label}
                  className="rounded-[var(--radius-lg)] border border-dashed border-border bg-muted/40 px-4 py-6 text-center text-xs font-semibold text-muted-foreground"
                >
                  Sample · {label}
                </div>
              ),
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            Illustrative layout only — not your live balances.
          </p>
        </section>

        <section className="space-y-3 border-y border-border py-10">
          <h2 className="text-2xl font-extrabold text-heading">
            Fair attribution
          </h2>
          <p className="max-w-2xl text-sm text-body">
            When more than one valid referral applies to the same purchase, an
            eligible event-specific host campaign takes priority for that item. A
            Pàdéyá-wide program may apply when no matching host campaign wins.
            Each eligible item can produce only one referral commission.
          </p>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Pàdéyá-wide program commission is funded by Pàdéyá. Host campaign
            commission follows that campaign’s host-funded rules.
          </p>
        </section>

        <section className="rounded-[var(--radius-xl)] border border-border p-6 sm:flex sm:items-center sm:justify-between sm:gap-6">
          <div>
            <h2 className="text-xl font-extrabold text-heading">
              Hosting an event?
            </h2>
            <p className="mt-2 max-w-xl text-sm text-body">
              Create event-specific ambassador campaigns for eligible tickets or
              merchandise from your host dashboard. Platform program creation
              stays with Pàdéyá.
            </p>
          </div>
          <div className="mt-4 sm:mt-0">
            {isHost ? (
              <Link
                href="/host/ambassadors/campaigns"
                onClick={() =>
                  track("host_campaign_cta_click", {
                    metadata: { destination_type: "host_campaigns" },
                    dedupeTtlMs: 2_000,
                  })
                }
              >
                <Button>Manage host campaigns</Button>
              </Link>
            ) : (
              <Link href="/host">
                <Button variant="secondary">Learn about hosting</Button>
              </Link>
            )}
          </div>
        </section>

        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-2xl font-extrabold text-heading">
                Open host campaigns
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Self-serve host campaigns you can join today. Pàdéyá-wide
                programs are not listed publicly when enrollment is private.
              </p>
            </div>
            <Link href="/ambassadors/events">
              <Button size="sm" variant="secondary">
                See all
              </Button>
            </Link>
          </div>
          {!eventsLoaded ? (
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
                onToggle={(e) => {
                  if ((e.target as HTMLDetailsElement).open) {
                    track("ambassador_faq_open", {
                      metadata: { question: item.q.slice(0, 80) },
                      dedupeTtlMs: 5_000,
                      dedupeScope: `faq:${item.q.slice(0, 40)}`,
                    });
                  }
                }}
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
          <h2 className="text-2xl font-extrabold">Ready when you are</h2>
          <p className="mt-2 max-w-lg text-sm text-subtle-foreground">
            Use your dashboard when enrolled, or browse open host campaigns to
            get started.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">{heroCtas}</div>
        </section>
      </Container>
    </main>
  );
}
