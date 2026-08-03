"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { EligibleEventsGrid } from "@/components/ambassadors/EligibleEventsGrid";
import { headerDarkSurfaceProps } from "@/components/layout/headerSurface";
import { Badge, Button, Container, SkeletonLoader } from "@/components/ui";
import { track } from "@/lib/analytics";
import { fetchDomainEligibleEvents } from "@/lib/ambassadors-api";
import {
  DUAL_COMMISSION_COPY,
  enrollmentScopeAnalytics,
  resolveOwnPlatformLinkPath,
  resolvePublicEnrollmentState,
  type PublicEnrollmentState,
} from "@/lib/ambassador-frontend-alignment";
import { brand } from "@/lib/brand";
import {
  fetchEligibleAmbassadorEvents,
  fetchMyReferralPrograms,
  fetchMyReferralSummary,
  type ReferralProgramRow,
  type ReferralSummary,
} from "@/lib/promos-api";
import type { EligibleAmbassadorEvent } from "@/lib/types/promos";

const FAQ = [
  {
    id: "who",
    q: "Who can become an Ambassador?",
    a: "Users may participate through eligible host event campaigns or through Pàdéyá-wide programs controlled by Pàdéyá. Availability depends on active programs, campaigns and enrollment.",
  },
  {
    id: "platform",
    q: "What is a Pàdéyá-wide program?",
    a: "A referral program created by Pàdéyá that may cover eligible tickets, merchandise or both across participating events. Its commission is funded by Pàdéyá and does not reduce the host’s settlement.",
  },
  {
    id: "host",
    q: "What is a host campaign?",
    a: "An event-specific referral campaign created by an event host. The host defines its ticket or merchandise rules and funds its commission.",
  },
  {
    id: "host-enable",
    q: "Do hosts need to enable Pàdéyá-wide programs?",
    a: "No. Pàdéyá-wide programs are managed and funded by Pàdéyá. Their commission does not reduce the host’s settlement. Hosts only enable Ambassadors when they want their own host-funded campaigns.",
  },
  {
    id: "links",
    q: "Do I get one referral link?",
    a: "Your Pàdéyá-wide enrollment uses your Fan Passport username link where available. Individual host campaigns may also provide campaign-specific links.",
  },
  {
    id: "multi",
    q: "Can I join more than one campaign?",
    a: "Yes — you can hold multiple host campaign enrollments and, when enrolled by Pàdéyá, a Pàdéyá-wide program. All of them appear in one ambassador dashboard.",
  },
  {
    id: "dual",
    q: "What happens if a host campaign and Pàdéyá-wide program both apply?",
    a: "When you are actively enrolled in both and the purchase item is eligible under both sets of rules, it may create two separate earnings: one funded by the host and one funded by Pàdéyá.",
  },
  {
    id: "live-only",
    q: "Does a live host campaign automatically make me eligible?",
    a: "No. You must be enrolled in that campaign. A live campaign without your enrollment does not create a host-funded earning for you.",
  },
  {
    id: "username-link",
    q: "What happens when I use my Pàdéyá-wide username link?",
    a: "It records your Pàdéyá-wide referral. Where you also hold a valid matching host enrollment, the same purchase may recognise both eligible earning pots.",
  },
  {
    id: "host-link",
    q: "What happens when I use a host campaign link?",
    a: "It records your host campaign referral. Where you also have an eligible active Pàdéyá-wide enrollment, the same purchase may also create a separate Pàdéyá-funded earning.",
  },
  {
    id: "who-pays",
    q: "Who pays my commission?",
    a: "Pàdéyá funds Pàdéyá-wide earnings. Event hosts fund earnings from their own campaigns.",
  },
  {
    id: "when",
    q: "When does commission become available?",
    a: "Eligible commission moves through pending, approved, payable and paid states according to the applicable hold and payout policy. Instant payout is not guaranteed.",
  },
  {
    id: "refund",
    q: "What happens after a refund?",
    a: "A full or partial refund may create separate reversal entries for each affected earning. The original earnings remain visible in your history.",
  },
  {
    id: "where",
    q: "Where can I see my results?",
    a: "Your ambassador dashboard combines Pàdéyá-wide programs and host campaigns while keeping each earning and payer clearly labelled.",
  },
] as const;

const EARNING_MODEL = [
  {
    title: "Platform enrollment only",
    result: "Pàdéyá-funded earning",
  },
  {
    title: "Host enrollment only",
    result: "Host-funded earning",
  },
  {
    title: "Both eligible enrollments",
    result: "Two separate earnings",
  },
  {
    title: "Neither enrollment",
    result: "No commission",
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
  const [copyAnnounce, setCopyAnnounce] = useState("");
  const dualSectionTracked = useRef(false);

  const signedIn = Boolean(user);
  const isHost = Boolean(
    user?.roles?.some((r) => r === "host" || r === "super_admin"),
  );

  useEffect(() => {
    track("ambassador_page_view", {
      metadata: {
        auth_state: signedIn ? "signed_in" : "signed_out",
        enrollment_scope: signedIn ? "loading" : "signed_out",
      },
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

  const ownLink = resolveOwnPlatformLinkPath(summary, programs);
  const scopeAnalytics = enrollmentScopeAnalytics(enrollmentState);

  useEffect(() => {
    if (dualSectionTracked.current) return;
    const el = document.getElementById("dual-earnings");
    if (!el || typeof IntersectionObserver === "undefined") return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          dualSectionTracked.current = true;
          track("ambassador_dual_earning_section_view", {
            metadata: {
              auth_state: signedIn ? "signed_in" : "signed_out",
              enrollment_scope: scopeAnalytics,
            },
            dedupeTtlMs: 60_000,
            dedupeScope: "ambassador_dual_earning_section_view",
          });
          obs.disconnect();
        }
      },
      { threshold: 0.35 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [signedIn, scopeAnalytics]);

  async function copyOwnLink() {
    if (!ownLink || typeof window === "undefined") return;
    const absolute = new URL(ownLink, window.location.origin).toString();
    try {
      await navigator.clipboard.writeText(absolute);
      setCopied(true);
      setCopyAnnounce("Pàdéyá referral link copied to clipboard");
      window.setTimeout(() => {
        setCopied(false);
        setCopyAnnounce("");
      }, 2000);
      track("ambassador_username_link_copy", {
        metadata: {
          auth_state: "signed_in",
          enrollment_scope: scopeAnalytics,
          destination_type: "copy_platform_link",
        },
        dedupeTtlMs: 2_000,
      });
    } catch {
      setCopied(false);
      setCopyAnnounce("Could not copy link. Try again.");
    }
  }

  function trackPrimary(destination: string, location = "hero") {
    track("ambassador_primary_cta_click", {
      metadata: {
        auth_state: signedIn ? "signed_in" : "signed_out",
        enrollment_scope: scopeAnalytics,
        destination_type: destination,
        location,
      },
      dedupeTtlMs: 2_000,
    });
  }

  function trackSecondary(destination: string, location = "hero") {
    track("ambassador_secondary_cta_click", {
      metadata: {
        auth_state: signedIn ? "signed_in" : "signed_out",
        enrollment_scope: scopeAnalytics,
        destination_type: destination,
        location,
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
            <Link
              href="/ambassadors/events"
              onClick={() => trackSecondary("browse_host_campaigns")}
            >
              <Button size="lg" variant="outline-dark">
                Browse open host campaigns
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
            <Link
              href="/ambassadors/events"
              onClick={() => trackSecondary("browse_host_campaigns")}
            >
              <Button size="lg" variant="outline-dark">
                Browse open host campaigns
              </Button>
            </Link>
            <p className="basis-full text-sm text-subtle-foreground">
              Pàdéyá-wide programs appear when Pàdéyá enrols you. Host campaigns
              require an eligible campaign enrollment.
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
            <Link
              href="/dashboard/ambassador"
              onClick={() => trackSecondary("view_host_campaigns")}
            >
              <Button size="lg" variant="outline-dark">
                View my host campaigns
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
              <Button
                size="lg"
                variant="outline-dark"
                aria-label={
                  copied
                    ? "Pàdéyá referral link copied"
                    : "Copy my Pàdéyá referral link"
                }
                onClick={() => void copyOwnLink()}
              >
                {copied ? "Link copied" : "Copy my Pàdéyá link"}
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
            <Link
              href="/dashboard/ambassador"
              onClick={() => trackSecondary("view_referral_links")}
            >
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
            <Link
              href="/dashboard/ambassador"
              onClick={() => trackPrimary("history")}
            >
              <Button size="lg" variant="outline-dark">
                View referral history
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
      <div className="sr-only" aria-live="polite">
        {copyAnnounce}
      </div>
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
            {DUAL_COMMISSION_COPY.heroSupport}
          </p>
          <div className="mt-8 flex flex-wrap gap-3">{heroCtas}</div>
          <p className="mt-5 max-w-2xl text-sm leading-relaxed text-subtle-foreground">
            {DUAL_COMMISSION_COPY.heroDisclaimer}
          </p>
        </Container>
      </section>

      <Container className="space-y-16 py-12 sm:py-16">
        <section
          aria-label="Ambassador features"
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5"
        >
          {[
            "Username-based Pàdéyá link",
            "Ticket and merchandise coverage",
            "Host + Pàdéyá earning pots",
            "One connected dashboard",
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
              Separate scopes inside one connected ambassador system — they can
              stack when you are enrolled in both.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-2">
            <article className="rounded-[var(--radius-xl)] border border-border bg-surface p-6">
              <Badge tone="success">Pàdéyá-wide</Badge>
              <h3 className="mt-3 text-xl font-extrabold text-heading">
                Pàdéyá-wide programs
              </h3>
              <p className="mt-2 text-sm text-body">
                Promote eligible tickets and merchandise across participating
                events with your Pàdéyá-wide referral link. Depending on the
                program, the link may cover tickets, merchandise or both.
              </p>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li>Commission funded by Pàdéyá</li>
                <li>Username-based referral link</li>
                <li>Tickets, merchandise or both</li>
                <li>Requires active Pàdéyá enrollment</li>
                <li>Can earn alongside an eligible host campaign</li>
              </ul>
              <p className="mt-4 text-xs text-muted-foreground">
                {DUAL_COMMISSION_COPY.settlementNote}
              </p>
              {signedIn &&
              (enrollmentState === "platform_only" ||
                enrollmentState === "both") ? (
                <Link
                  href="/dashboard/ambassador"
                  className="mt-5 inline-block"
                  onClick={() =>
                    track("ambassador_scope_card_click", {
                      metadata: {
                        scope: "platform",
                        enrollment_scope: scopeAnalytics,
                      },
                      dedupeTtlMs: 2_000,
                    })
                  }
                >
                  <Button size="sm">View my programs</Button>
                </Link>
              ) : (
                <p className="mt-5 text-xs text-muted-foreground">
                  Pàdéyá-wide access is enrollment-controlled — not open join.
                </p>
              )}
            </article>
            <article className="rounded-[var(--radius-xl)] border border-border bg-surface p-6">
              <Badge tone="neutral">Host campaign</Badge>
              <h3 className="mt-3 text-xl font-extrabold text-heading">
                Host event campaigns
              </h3>
              <p className="mt-2 text-sm text-body">
                Promote a specific event through a ticket or merchandise
                campaign created by its host.
              </p>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li>Event-specific</li>
                <li>Commission funded by the host</li>
                <li>Requires active campaign enrollment</li>
                <li>Rules are managed by the host</li>
                <li>Can earn alongside an eligible Pàdéyá-wide program</li>
              </ul>
              <p className="mt-4 text-xs text-muted-foreground">
                {DUAL_COMMISSION_COPY.hostEnrollmentRequired}
              </p>
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
                    metadata: {
                      scope: "host",
                      enrollment_scope: scopeAnalytics,
                    },
                    dedupeTtlMs: 2_000,
                  })
                }
              >
                <Button size="sm" variant="secondary">
                  {signedIn &&
                  (enrollmentState === "host_only" || enrollmentState === "both")
                    ? "View my host campaigns"
                    : "Browse open host campaigns"}
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
                body: "Join an eligible host campaign or get enrolled in a Pàdéyá-wide program. You may participate in one scope or both.",
              },
              {
                step: "02",
                title: "Receive your links",
                body: "Your Pàdéyá-wide program uses your Fan Passport username link where available. Individual host campaigns may also provide campaign-specific links.",
              },
              {
                step: "03",
                title: "Share eligible experiences",
                body: "Promote covered events, tickets and merchandise. Using either valid link may recognise both of your eligible enrollments when you are enrolled in both scopes.",
              },
              {
                step: "04",
                title: "Track both earnings",
                body: "See host-funded and Pàdéyá-funded earnings separately in one ambassador dashboard.",
              },
              {
                step: "05",
                title: "Receive approved payouts",
                body: "Eligible commission progresses through pending, approved, payable and paid states. Refunds may create separate reversal entries.",
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

        <section
          id="username-link"
          className="rounded-[var(--radius-xl)] border border-border bg-surface p-6 sm:p-8"
          aria-labelledby="username-link-heading"
        >
          <h2
            id="username-link-heading"
            className="text-2xl font-extrabold text-heading"
          >
            Your Pàdéyá-wide link
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-body">
            When you have an active Pàdéyá-wide enrollment, your referral link
            uses your Fan Passport username where available. Share it to promote
            eligible experiences covered by your program.
          </p>
          <p className="mt-4 break-all font-mono text-base text-heading sm:text-lg">
            {ownLink &&
            (enrollmentState === "platform_only" || enrollmentState === "both")
              ? ownLink.startsWith("http")
                ? ownLink.replace(/^https?:\/\//, "")
                : `padeya.com${ownLink.startsWith("/") ? ownLink : `/${ownLink}`}`
              : DUAL_COMMISSION_COPY.usernameExample}
          </p>
          {ownLink &&
          (enrollmentState === "platform_only" || enrollmentState === "both") ? (
            <p className="mt-1 text-xs text-muted-foreground">Your active link</p>
          ) : (
            <p className="mt-1 text-xs text-muted-foreground">
              Illustrative example — not a live account link
            </p>
          )}
          <p className="mt-4 max-w-2xl text-sm text-muted-foreground">
            Host event campaigns may still provide separate campaign links. When
            you are eligible in both scopes, either valid link may recognise both
            of your enrollments for the same eligible purchase.
          </p>
          {ownLink &&
          (enrollmentState === "platform_only" || enrollmentState === "both") ? (
            <Button
              size="sm"
              className="mt-5"
              aria-label={
                copied
                  ? "Pàdéyá referral link copied"
                  : "Copy my Pàdéyá referral link"
              }
              onClick={() => void copyOwnLink()}
            >
              {copied ? "Link copied" : "Copy my Pàdéyá link"}
            </Button>
          ) : null}
        </section>

        <section className="space-y-6 rounded-[var(--radius-xl)] border border-border bg-surface p-6 sm:p-8">
          <div>
            <h2 className="text-2xl font-extrabold text-heading">
              Everything in one ambassador dashboard
            </h2>
            <p className="mt-2 max-w-2xl text-sm text-body">
              Platform and Host badges, username-based Pàdéyá links, host
              campaign links, clicks, converted orders, attributed items,
              pending and available commission, paid totals, reversals, and
              payer separation — connected in one place. One attributed item can
              still produce up to two separate commission earnings.
            </p>
          </div>

          <div
            className="rounded-[var(--radius-lg)] border border-dashed border-border bg-background/60 p-4 sm:p-5"
            role="img"
            aria-label="Illustrative example: one ticket purchase with separate host-funded and Pàdéyá-funded earnings"
          >
            <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-accent">
              Illustrative example
            </p>
            <p className="mt-3 text-sm font-semibold text-heading">
              Sample earning · Sunday Comedy Room ticket
            </p>
            <div className="mt-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
                <div>
                  <Badge tone="neutral">Host campaign</Badge>
                  <p className="mt-1 text-xs text-muted-foreground">Host-funded</p>
                </div>
                <p className="font-mono text-sm text-heading">₦1,000</p>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
                <div>
                  <Badge tone="success">Pàdéyá-wide program</Badge>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Funded by Pàdéyá
                  </p>
                </div>
                <p className="font-mono text-sm text-heading">₦500</p>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold text-heading">
                  Total commission
                </p>
                <p className="font-mono text-sm font-semibold text-heading">
                  ₦1,500
                </p>
              </div>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              One converted order · one attributed item · two separate earnings —
              not your live balances.
            </p>
          </div>

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
                    enrollment_scope: scopeAnalytics,
                  },
                  dedupeTtlMs: 2_000,
                })
              }
            >
              <Button size="sm">
                {enrollmentState === "both"
                  ? "Open unified dashboard"
                  : enrollmentState === "inactive"
                    ? "View referral history"
                    : "Open ambassador dashboard"}
              </Button>
            </Link>
          ) : null}
        </section>

        <section
          id="dual-earnings"
          className="space-y-5 border-y border-border py-10"
          aria-labelledby="dual-earnings-heading"
        >
          <div>
            <h2
              id="dual-earnings-heading"
              className="text-2xl font-extrabold text-heading"
            >
              {DUAL_COMMISSION_COPY.dualEarningsTitle}
            </h2>
            <p className="sr-only">{DUAL_COMMISSION_COPY.dualEarningsSr}</p>
            <p className="mt-2 max-w-2xl text-sm text-body">
              Pàdéyá-wide programs and host campaigns are separate earning
              opportunities. When you are actively enrolled in both a Pàdéyá-wide
              program and an eligible host campaign, the same referred purchase
              item may create two commission earnings: one funded by the host and
              another funded by Pàdéyá.
            </p>
            <p className="mt-3 max-w-2xl text-sm text-muted-foreground">
              Each earning is calculated and recorded independently. Hosts only
              fund commission from their own campaigns. Pàdéyá-wide commission is
              paid separately and does not reduce the host’s settlement. A
              campaign or program must be active, your enrollment must be valid,
              and the purchase must meet its eligibility rules.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {EARNING_MODEL.map((row) => (
              <div
                key={row.title}
                className="rounded-[var(--radius-lg)] border border-border bg-surface px-4 py-4"
              >
                <p className="text-sm font-semibold text-heading">{row.title}</p>
                <p className="mt-2 text-xs text-muted-foreground">→ {row.result}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-[var(--radius-xl)] border border-border p-6 sm:flex sm:items-center sm:justify-between sm:gap-6">
          <div>
            <h2 className="text-xl font-extrabold text-heading">
              Hosting an event?
            </h2>
            <p className="mt-2 max-w-xl text-sm text-body">
              Create event-specific ambassador campaigns for eligible tickets or
              merchandise. Only ambassadors enrolled in your campaign can earn
              the host-funded commission. Where an ambassador is also enrolled in
              an eligible Pàdéyá-wide program, Pàdéyá may fund a separate earning
              without reducing your settlement.
            </p>
          </div>
          <div className="mt-4 shrink-0 sm:mt-0">
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
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
                These are host event campaigns — enrollment is required and
                commission is host-funded. Joining a host campaign does not
                automatically create a Pàdéyá-wide enrollment. If you are already
                enrolled platform-wide, both pots may apply where both scopes are
                eligible.
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
                key={item.id}
                className="group border-b border-border pb-4"
                onToggle={(e) => {
                  if ((e.target as HTMLDetailsElement).open) {
                    track("ambassador_faq_open", {
                      metadata: {
                        faq_id: item.id,
                        enrollment_scope: scopeAnalytics,
                      },
                      dedupeTtlMs: 5_000,
                      dedupeScope: `faq:${item.id}`,
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
            Use your ambassador dashboard to manage your links, track eligible
            referrals and see host-funded and Pàdéyá-funded earnings separately.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">{heroCtas}</div>
        </section>
      </Container>
    </main>
  );
}
