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
    a: "Users may join host campaigns that a host has enabled, or be enrolled in a Pàdéyá-wide program by Pàdéyá. Platform-wide enrollment is currently managed by Pàdéyá — not open self-serve.",
  },
  {
    q: "What is a Pàdéyá-wide program?",
    a: "A referral program created by Pàdéyá. By default it covers tickets and merchandise across events under the program’s rules — hosts do not need to enable anything. Your platform link uses your Pàdéyá username when you have one. Commission is funded by Pàdéyá. Admins may exclude specific hosts or events.",
  },
  {
    q: "What is a host campaign?",
    a: "An event-specific referral campaign that only exists after a host enables Ambassadors for that event’s tickets and/or merchandise. Rules and funding follow that host campaign.",
  },
  {
    q: "Do hosts need to enable Pàdéyá-wide programs?",
    a: "No. Pàdéyá-wide coverage is the platform default for enrolled ambassadors. Hosts only enable Ambassadors when they want their own event-scoped, host-funded campaigns.",
  },
  {
    q: "Do I get one referral link?",
    a: "Your Pàdéyá-wide link is normally /r/{your-username}. Each host campaign enrollment can also have its own code. One username link can unlock both pots when you are enrolled in both scopes for that event.",
  },
  {
    q: "Can I join more than one campaign?",
    a: "Yes — you can hold multiple host campaign enrollments and, when enrolled by Pàdéyá, a platform-wide program. All of them appear in one ambassador dashboard.",
  },
  {
    q: "What happens if a host campaign and Pàdéyá-wide both apply?",
    a: "Both can pay on the same item: host-funded commission for your host enrollment and Pàdéyá-funded commission for your platform enrollment. Enabling a host campaign does not cancel platform earnings.",
  },
  {
    q: "Who pays the commission?",
    a: "Pàdéyá funds Pàdéyá-wide program commission. Host event campaign commission follows that campaign’s host-funded rules. On a dual item, both payers can owe separately.",
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
            Enrolled Pàdéyá-wide ambassadors promote across events and merch by
            default — hosts do not need to opt in. Hosts can also enable their own
            event campaigns. Share your link and track results in one dashboard.
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
                Promote across Pàdéyá with one program link. By default, coverage
                includes tickets and merchandise under the program’s rules — hosts
                do not need to mark their events for Pàdéyá-wide to apply.
              </p>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li>One program link</li>
                <li>Default across events and merch (program rules)</li>
                <li>No host opt-in required</li>
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
                Hosts enable Ambassadors per event when they want their own
                campaign. Ticketing and/or merch coverage starts only after they
                turn it on for that event.
              </p>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li>Host must enable (tick) per event</li>
                <li>Ticket and/or merch — chosen by host</li>
                <li>Host-funded campaign rules</li>
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
                body: "Your Pàdéyá-wide link is normally /r/{your-username}. Host campaign enrollments can have their own codes. One username link can unlock both pots when you are enrolled in both scopes.",
              },
              {
                step: "03",
                title: "Share eligible experiences",
                body: "Pàdéyá-wide links cover events and merch by default under program rules. Host campaigns cover only the event the host enabled.",
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

        <section className="space-y-6 rounded-[var(--radius-xl)] border border-border bg-surface p-6 sm:p-8">
          <div>
            <h2 className="text-2xl font-extrabold text-heading">
              Everything in one ambassador dashboard
            </h2>
            <p className="mt-2 max-w-2xl text-sm text-body">
              Platform and host activity stay connected — links, clicks,
              converted orders, commission states, and reversals in one place.
              Filter by tickets or merchandise without switching tools.
            </p>
          </div>

          <div
            className="grid gap-4 lg:grid-cols-3"
            aria-hidden
          >
            <div className="rounded-[var(--radius-lg)] border border-border bg-background/60 p-4">
              <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-muted-foreground">
                Sample · Scopes
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge tone="success">Pàdéyá-wide</Badge>
                <Badge tone="neutral">Host campaign</Badge>
                <Badge tone="outline">Tickets</Badge>
                <Badge tone="outline">Merchandise</Badge>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                Badges show which enrollments are active for you.
              </p>
            </div>

            <div className="rounded-[var(--radius-lg)] border border-border bg-background/60 p-4">
              <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-muted-foreground">
                Sample · Your link
              </p>
              <p className="mt-3 font-mono text-sm text-heading">
                /r/your-username
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                Platform-wide uses your username when set. Host campaigns can
                add event-specific codes alongside it.
              </p>
            </div>

            <div className="rounded-[var(--radius-lg)] border border-border bg-background/60 p-4">
              <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-muted-foreground">
                Sample · What you track
              </p>
              <ul className="mt-3 space-y-1.5 text-xs text-muted-foreground">
                <li>Clicks and converted orders</li>
                <li>Attributed items</li>
                <li>Pending · approved · payable · paid</li>
                <li>Host-funded and Pàdéyá-funded pots</li>
                <li>Reversals after refunds</li>
              </ul>
            </div>
          </div>

          <p className="text-xs text-muted-foreground">
            Illustrative layout only — not your live balances or account data.
          </p>

          {signedIn &&
          (enrollmentState === "platform_only" ||
            enrollmentState === "host_only" ||
            enrollmentState === "both" ||
            enrollmentState === "inactive") ? (
            <Link
              href="/dashboard/ambassador"
              onClick={() =>
                track("ambassador_dashboard_cta_click", {
                  metadata: {
                    location: "dashboard_preview",
                    enrollment_state: enrollmentState,
                  },
                  dedupeTtlMs: 2_000,
                })
              }
            >
              <Button size="sm">
                {enrollmentState === "both"
                  ? "Open unified dashboard"
                  : "Open ambassador dashboard"}
              </Button>
            </Link>
          ) : null}
        </section>

        <section className="space-y-4 border-y border-border py-10">
          <div>
            <h2 className="text-2xl font-extrabold text-heading">
              Fair attribution
            </h2>
            <p className="mt-2 max-w-2xl text-sm text-body">
              When you are enrolled in both a host campaign and a Pàdéyá-wide
              program, an eligible ticket or merchandise item can earn two
              commissions — one host-funded and one funded by Pàdéyá. Your
              platform link uses your username when available
              (<span className="whitespace-nowrap"> /r/your-username</span>).
            </p>
          </div>
          <ul className="max-w-2xl space-y-2 text-sm text-muted-foreground">
            <li>
              Platform-only enrollment: Pàdéyá pays. Host settlement is not
              reduced.
            </li>
            <li>
              Host-campaign-only enrollment: the host campaign pays under its
              rules.
            </li>
            <li>
              Both enrollments on the same event or product: both pots can apply
              on the same item.
            </li>
            <li>
              A host enabling Ambassadors alone does not create a host earner —
              you still need an enrollment for that campaign.
            </li>
            <li>
              Refunds may reverse each related commission while your earnings
              history stays visible.
            </li>
          </ul>
        </section>

        <section className="rounded-[var(--radius-xl)] border border-border p-6 sm:flex sm:items-center sm:justify-between sm:gap-6">
          <div>
            <h2 className="text-xl font-extrabold text-heading">
              Hosting an event?
            </h2>
            <p className="mt-2 max-w-xl text-sm text-body">
              Pàdéyá-wide programs already cover events and merch by default —
              you do not need to enable anything for that. Enable host campaigns
              only when you want your own event-scoped, host-funded Ambassadors
              for tickets and/or merchandise.
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
