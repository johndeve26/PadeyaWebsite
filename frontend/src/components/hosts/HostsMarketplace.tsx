"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { DiscoveryBranchCard } from "@/components/home/DiscoveryBranchCard";
import { HostMarketplaceCard } from "@/components/hosts/HostMarketplaceCard";
import { HostRecommendationsSection } from "@/components/personal/command-center/HostRecommendationsSection";
import { headerDarkSurfaceProps } from "@/components/layout/headerSurface";
import {
  Badge,
  Button,
  Card,
  Container,
  CTASection,
  Input,
  SectionHeader,
} from "@/components/ui";
import {
  trackHostFilterUsed,
  trackLegacyLookupSubmit,
} from "@/lib/analytics";
import { fetchMyFollowing } from "@/lib/crm-api";
import {
  categoryBrowseImage,
  cityBrowseImage,
  collectionBrowseImage,
} from "@/lib/discovery/browse-images";
import { SPONSORSHIP_HOSTS_PATH } from "@/lib/sponsor-marketplace-paths";
import {
  DEMO_DISCOVER_HOSTS,
  DEMO_LEGACY_QUICK_LINKS,
} from "@/lib/hosts-demo";
import { timeoutOrErrorMessage } from "@/lib/api-timeouts";
import { fetchDiscoverHosts, fetchHostRecommendations } from "@/lib/hosts-api";
import type { HostDiscovery } from "@/lib/types/hosts-discovery";

const FEATURED_LIMIT = 3;
const DIRECTORY_DESKTOP = 6;
const DIRECTORY_MOBILE = 3;

const CATEGORY_BROWSE = [
  {
    id: "music",
    label: "Music",
    hint: "Concerts, DJs, live stages",
    href: "/events/c/music",
    image: categoryBrowseImage("music"),
  },
  {
    id: "nightlife",
    label: "Nightlife",
    hint: "Parties and late nights",
    href: "/events/c/nightlife",
    image: categoryBrowseImage("nightlife"),
  },
  {
    id: "comedy",
    label: "Comedy",
    hint: "Open mics and headliners",
    href: "/events/c/comedy",
    image: categoryBrowseImage("comedy"),
  },
  {
    id: "tech",
    label: "Tech",
    hint: "Builders and mixers",
    href: "/events/c/tech",
    image: categoryBrowseImage("tech"),
  },
  {
    id: "gospel",
    label: "Gospel",
    hint: "Worship and faith nights",
    href: "/events/c/gospel",
    image: categoryBrowseImage("gospel"),
  },
  {
    id: "campus",
    label: "Campus",
    hint: "Student energy",
    href: "/events/c/campus",
    image: categoryBrowseImage("campus"),
  },
  {
    id: "lifestyle",
    label: "Lifestyle",
    hint: "Food, culture, pop-ups",
    href: "/events/c/lifestyle",
    image: categoryBrowseImage("lifestyle"),
  },
  {
    id: "business",
    label: "Business",
    hint: "Founders and networks",
    href: "/events/c/business",
    image: categoryBrowseImage("business"),
  },
  {
    id: "sponsor-ready",
    label: "Sponsor-ready",
    hint: "Hosts open to brand partners",
    href: null as string | null,
    image: collectionBrowseImage(SPONSORSHIP_HOSTS_PATH),
  },
  {
    id: "vault-enabled",
    label: "Vault enabled",
    hint: "Hosts with Vault drops",
    href: null as string | null,
    image: collectionBrowseImage("/hosts"),
  },
] as const;

const LOCATION_BROWSE = [
  {
    id: "Lagos",
    label: "Lagos",
    hint: "Island and mainland scenes",
    href: "/events/city/lagos",
    image: cityBrowseImage("lagos"),
  },
  {
    id: "Ibadan",
    label: "Ibadan",
    hint: "Ancient city pulse",
    href: "/events/city/ibadan",
    image: cityBrowseImage("ibadan"),
  },
  {
    id: "Abuja",
    label: "Abuja",
    hint: "Capital nights",
    href: "/events/city/abuja",
    image: cityBrowseImage("abuja"),
  },
  {
    id: "Akure",
    label: "Akure",
    hint: "Ondo energy",
    href: "/events/city/akure",
    image: cityBrowseImage("akure"),
  },
  {
    id: "Lekki",
    label: "Lekki",
    hint: "Peninsula nights",
    href: "/events/area/lekki",
    image: cityBrowseImage("lagos"),
  },
  {
    id: "Victoria Island",
    label: "Victoria Island",
    hint: "Island energy",
    href: "/events/area/victoria-island",
    image: cityBrowseImage("lagos"),
  },
  {
    id: "Ikeja",
    label: "Ikeja",
    hint: "Mainland pulse",
    href: "/events/area/ikeja",
    image: cityBrowseImage("lagos"),
  },
  {
    id: "Yaba",
    label: "Yaba",
    hint: "Tech and campus",
    href: "/events/area/yaba",
    image: cityBrowseImage("lagos"),
  },
] as const;

const WHY_FOLLOW = [
  {
    title: "See what they host next",
    body: "Follow upcoming events and drops from creators you trust.",
  },
  {
    title: "Trust verified reviews",
    body: "Reviews come from people who actually checked in with Pàdéyá tickets.",
  },
  {
    title: "Unlock Vault content",
    body: "Access exclusive drops, recaps, early access, and ticket-holder content.",
  },
  {
    title: "Watch their Legacy grow",
    body: "Every event, review, and memory builds a public reputation trail.",
  },
] as const;

const PROOF_CHIPS = [
  "Verified reviews",
  "Legacy tiers",
  "Upcoming events",
  "Vault drops",
  "Sponsor-ready hosts",
] as const;

function matchesCategory(host: HostDiscovery, chipId: string): boolean {
  if (chipId === "sponsor-ready") return host.sponsor_ready;
  if (chipId === "vault-enabled") return host.vault_items_count > 0;
  const hay = `${host.primary_category || ""} ${host.host_type || ""}`.toLowerCase();
  return hay.includes(chipId);
}

function matchesLocation(host: HostDiscovery, locationId: string): boolean {
  const city = (host.primary_city || "").toLowerCase();
  const nextCity = (host.next_upcoming_event?.city || "").toLowerCase();
  const target = locationId.toLowerCase();
  return city.includes(target) || nextCity.includes(target);
}

function countHostsForCategory(
  hosts: HostDiscovery[],
  chipId: string,
): number {
  return hosts.filter((h) => matchesCategory(h, chipId)).length;
}

function countHostsForLocation(
  hosts: HostDiscovery[],
  locationId: string,
): number {
  return hosts.filter((h) => matchesLocation(h, locationId)).length;
}

function HostsMarketplaceInner({
  initialHosts = [],
}: {
  initialHosts?: HostDiscovery[];
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sortRecommended = searchParams.get("sort") === "recommended";
  const { user } = useAuth();
  const [clientHosts, setClientHosts] = useState<HostDiscovery[] | null>(null);
  const [recRank, setRecRank] = useState<Map<string, number>>(() => new Map());
  const hosts =
    initialHosts.length > 0
      ? initialHosts
      : clientHosts && clientHosts.length > 0
        ? clientHosts
        : DEMO_DISCOVER_HOSTS;
  const [username, setUsername] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [locationFilter, setLocationFilter] = useState<string | null>(null);
  const [directoryExpanded, setDirectoryExpanded] = useState(false);
  const [clientLoadError, setClientLoadError] = useState<string | null>(null);
  const [followingIds, setFollowingIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [followingUsernames, setFollowingUsernames] = useState<Set<string>>(
    () => new Set(),
  );

  useEffect(() => {
    if (initialHosts.length > 0) return;
    let cancelled = false;
    void fetchDiscoverHosts()
      .then((rows) => {
        if (cancelled) return;
        setClientLoadError(null);
        if (rows.length > 0) setClientHosts(rows);
      })
      .catch((err) => {
        if (!cancelled) {
          setClientLoadError(
            timeoutOrErrorMessage(err, "Could not load hosts. Please try again."),
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [initialHosts.length]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      try {
        const rows = await fetchMyFollowing();
        if (!cancelled) {
          setFollowingIds(new Set(rows.map((r) => r.host_id)));
          setFollowingUsernames(new Set(rows.map((r) => r.username)));
        }
      } catch {
        if (!cancelled) {
          setFollowingIds(new Set());
          setFollowingUsernames(new Set());
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  useEffect(() => {
    if (!user || !sortRecommended) {
      setRecRank(new Map());
      return;
    }
    let cancelled = false;
    void fetchHostRecommendations({ limit: 50 })
      .then((res) => {
        if (cancelled) return;
        const next = new Map<string, number>();
        res.items.forEach((item, index) => {
          next.set(item.host.host_id, item.score * 1000 - index);
        });
        setRecRank(next);
      })
      .catch(() => {
        if (!cancelled) setRecRank(new Map());
      });
    return () => {
      cancelled = true;
    };
  }, [user, sortRecommended]);

  function setDirectorySort(mode: "marketplace" | "recommended") {
    const params = new URLSearchParams(searchParams.toString());
    if (mode === "recommended") params.set("sort", "recommended");
    else params.delete("sort");
    const q = params.toString();
    router.push(q ? `/hosts?${q}` : "/hosts", { scroll: false });
  }

  function hostIsFollowed(host: HostDiscovery): boolean {
    if (!user) return false;
    return (
      followingIds.has(host.host_id) ||
      followingUsernames.has(host.username)
    );
  }

  const featured = useMemo(() => {
    return [...hosts]
      .filter((h) => h.verified)
      .sort((a, b) => {
        const score =
          (b.upcoming_events_count || 0) + (b.tickets_sold_count || 0) -
          ((a.upcoming_events_count || 0) + (a.tickets_sold_count || 0));
        return score;
      })
      .slice(0, FEATURED_LIMIT);
  }, [hosts]);

  const featuredIds = useMemo(
    () => new Set(featured.map((h) => h.host_id)),
    [featured],
  );

  const categoryBrowse = useMemo(() => {
    return CATEGORY_BROWSE.map((chip) => ({
      ...chip,
      count: countHostsForCategory(hosts, chip.id),
    })).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
  }, [hosts]);

  const locationBrowse = useMemo(() => {
    return LOCATION_BROWSE.map((chip) => ({
      ...chip,
      count: countHostsForLocation(hosts, chip.id),
    })).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
  }, [hosts]);

  const directory = useMemo(() => {
    const filtered = hosts.filter((host) => {
      if (categoryFilter && !matchesCategory(host, categoryFilter)) return false;
      if (locationFilter && !matchesLocation(host, locationFilter)) return false;
      return true;
    });
    let list = filtered;
    // Avoid repeating the editorial trio when browsing unfiltered.
    if (!categoryFilter && !locationFilter) {
      list = filtered.filter((h) => !featuredIds.has(h.host_id));
    }
    if (sortRecommended && user && recRank.size > 0) {
      list = [...list].sort(
        (a, b) => (recRank.get(b.host_id) ?? -1) - (recRank.get(a.host_id) ?? -1),
      );
    }
    return list;
  }, [
    hosts,
    categoryFilter,
    locationFilter,
    featuredIds,
    sortRecommended,
    user,
    recRank,
  ]);

  const directoryVisible = directoryExpanded
    ? directory
    : directory.slice(0, DIRECTORY_DESKTOP);
  const directoryCanExpand = directory.length > DIRECTORY_MOBILE;

  function onLookup(event: FormEvent) {
    event.preventDefault();
    const slug = username.trim().replace(/^@/, "");
    if (!slug) return;
    trackLegacyLookupSubmit({ username: slug });
    router.push(`/@${slug}`);
  }

  function selectCategory(id: string) {
    const next = categoryFilter === id ? null : id;
    setCategoryFilter(next);
    setDirectoryExpanded(false);
    if (next) {
      trackHostFilterUsed({ filterType: "category", value: next });
      document
        .getElementById("host-directory")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function selectLocation(id: string) {
    const next = locationFilter === id ? null : id;
    setLocationFilter(next);
    setDirectoryExpanded(false);
    if (next) {
      trackHostFilterUsed({ filterType: "location", value: next });
      document
        .getElementById("host-directory")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  return (
    <main className="min-w-0 overflow-x-clip bg-background">
      {clientLoadError ? (
        <Container className="pt-6">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">
            <p>{clientLoadError}</p>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => {
                setClientLoadError(null);
                void fetchDiscoverHosts()
                  .then((rows) => {
                    setClientLoadError(null);
                    if (rows.length > 0) setClientHosts(rows);
                  })
                  .catch((err) => {
                    setClientLoadError(
                      timeoutOrErrorMessage(
                        err,
                        "Could not load hosts. Please try again.",
                      ),
                    );
                  });
              }}
            >
              Retry
            </Button>
          </div>
        </Container>
      ) : null}
      <section
        {...headerDarkSurfaceProps}
        className="relative overflow-hidden bg-ink text-paper"
      >
        <div aria-hidden className="padeya-hero-glow pointer-events-none absolute inset-0" />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-gradient-to-br from-ink via-ink/90 to-[color-mix(in_srgb,var(--primary)_12%,transparent)]"
        />
        <Container className="relative space-y-6 py-12 sm:py-14">
          <Badge tone="accent">Legacy marketplace</Badge>
          <h1 className="max-w-3xl text-3xl font-extrabold tracking-tight sm:text-5xl">
            Hosts with Legacy — not just a flyer.
          </h1>
          <p className="max-w-2xl text-base leading-relaxed text-paper/75 sm:text-lg">
            Follow creators who sell tickets, check guests in, collect verified
            reviews, drop Vault content, and grow on Pàdéyá. Every Legacy Page is
            a public home for what’s next.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <a href="#featured-hosts">
              <Button size="lg" className="w-full sm:w-auto">
                Browse verified hosts
              </Button>
            </a>
            <Link href="/host/onboarding">
              <Button
                size="lg"
                variant="outline-dark"
                className="w-full sm:w-auto"
              >
                Start hosting
              </Button>
            </Link>
          </div>
          <ul className="flex flex-wrap gap-2.5 pt-1">
            {PROOF_CHIPS.map((chip) => (
              <li
                key={chip}
                className="inline-flex items-center gap-2 rounded-full border border-paper/12 bg-ink/40 px-3.5 py-2 text-sm font-semibold text-paper/80 backdrop-blur-sm"
              >
                <span
                  aria-hidden
                  className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary"
                />
                {chip}
              </li>
            ))}
          </ul>
        </Container>
      </section>

      <Container className="space-y-10 py-10 sm:space-y-12 sm:py-12">
        <section className="space-y-4">
          <SectionHeader
            eyebrow="Jump in"
            title="Jump to a Legacy Page"
            description="Enter a username to open a host’s public profile."
          />
          <Card
            padded
            variant="muted"
            className="space-y-4 border border-border bg-[linear-gradient(135deg,color-mix(in_srgb,var(--primary)_8%,transparent),transparent_55%)]"
          >
            <form
              className="flex flex-col gap-3 sm:flex-row sm:items-start"
              onSubmit={onLookup}
            >
              <div className="min-w-0 flex-1">
                <Input
                  label="Username"
                  hint="Without the @ — e.g. djmaze"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="djmaze"
                  autoComplete="off"
                />
              </div>
              <Button
                type="submit"
                size="lg"
                className="mt-[1.375rem] w-full sm:w-auto"
              >
                Open Legacy
              </Button>
            </form>
            <div className="space-y-2">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                Try a demo host
              </p>
              <div className="flex flex-wrap gap-2">
                {DEMO_LEGACY_QUICK_LINKS.map((link) => (
                  <Link
                    key={link.username}
                    href={`/@${link.username}`}
                    onClick={() =>
                      trackLegacyLookupSubmit({ username: link.username })
                    }
                    className="rounded-full border border-border bg-surface-elevated px-3 py-1.5 text-sm font-semibold text-foreground transition hover:border-border-strong"
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>
          </Card>
        </section>

        {user ? (
          <HostRecommendationsSection
            variant="rail"
            limit={8}
            surface="hosts_recommended_rail"
            title="Recommended for you"
            seeAllHref="/hosts?sort=recommended"
          />
        ) : null}

        <section id="featured-hosts" className="scroll-mt-24 space-y-5">
          <SectionHeader
            eyebrow="Featured"
            title="Verified hosts building real event history"
            description="A shortlist of creators with checked-in proof and public Legacy Pages."
            action={
              <a href="#host-directory">
                <Button variant="secondary" size="md">
                  Browse directory
                </Button>
              </a>
            }
          />
          <div className="grid auto-rows-fr gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {featured.map((host, index) => (
              <div
                key={host.host_id}
                className={index >= 2 ? "hidden sm:block" : undefined}
              >
                <HostMarketplaceCard
                  host={host}
                  initiallyFollowing={hostIsFollowed(host)}
                />
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-4">
          <SectionHeader
            eyebrow="Scene"
            title="Find hosts by scene"
            description="Filter the directory by interest, or open the matching event hub."
          />
          <div className="rounded-[var(--radius-lg)] border border-border bg-muted/35 p-4 sm:p-5">
            <ul className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
              {categoryBrowse.map((chip) => {
                const active = categoryFilter === chip.id;
                return (
                  <li key={chip.id} className="h-full">
                    <DiscoveryBranchCard
                      item={{
                        label: chip.label,
                        hint: chip.hint,
                        href: chip.href || "#host-directory",
                        image: chip.image,
                        count: chip.count,
                        countNoun: "host",
                      }}
                      onClick={() => selectCategory(chip.id)}
                      pressed={active}
                      tone={chip.count > 0 && categoryBrowse[0]?.id === chip.id ? "accent" : "default"}
                      className={
                        active
                          ? "border-ink shadow-[var(--shadow-soft)] ring-1 ring-ink"
                          : undefined
                      }
                    />
                  </li>
                );
              })}
            </ul>
            <p className="mt-3 text-xs text-muted-foreground">
              Sorted by host density. Tap a scene to filter hosts below.
            </p>
          </div>
        </section>

        <section className="space-y-4">
          <SectionHeader
            eyebrow="Places"
            title="Find hosts by city"
            description="See hosts tied to a city or area — then jump into that location’s events."
          />
          <div className="rounded-[var(--radius-lg)] border border-border bg-muted/35 p-4 sm:p-5">
            <ul className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
              {locationBrowse.map((chip) => {
                const active = locationFilter === chip.id;
                return (
                  <li key={chip.id} className="h-full">
                    <DiscoveryBranchCard
                      item={{
                        label: chip.label,
                        hint: chip.hint,
                        href: chip.href,
                        image: chip.image,
                        count: chip.count,
                        countNoun: "host",
                      }}
                      onClick={() => selectLocation(chip.id)}
                      pressed={active}
                      tone={chip.count > 0 && locationBrowse[0]?.id === chip.id ? "accent" : "default"}
                      className={
                        active
                          ? "border-accent shadow-[var(--shadow-soft)] ring-1 ring-accent/60"
                          : undefined
                      }
                    />
                  </li>
                );
              })}
            </ul>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
              {locationBrowse
                .filter((c) => c.count > 0)
                .slice(0, 4)
                .map((chip) => (
                  <Link
                    key={`events-${chip.id}`}
                    href={chip.href}
                    className="font-semibold text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                  >
                    Events in {chip.label}
                  </Link>
                ))}
            </div>
          </div>
        </section>

        <section id="host-directory" className="scroll-mt-24 space-y-5">
          <SectionHeader
            eyebrow="Directory"
            title="Browse host Legacy Pages"
            description={
              categoryFilter || locationFilter
                ? "Showing hosts that match your filters. Clear filters to widen the list."
                : "Explore more creators beyond the featured shortlist."
            }
            action={
              <div className="flex flex-wrap items-center gap-2">
                <label className="sr-only" htmlFor="host-directory-sort">
                  Sort hosts
                </label>
                <select
                  id="host-directory-sort"
                  className="rounded-md border border-border bg-surface-elevated px-3 py-2 text-sm font-semibold"
                  value={sortRecommended ? "recommended" : "marketplace"}
                  onChange={(e) =>
                    setDirectorySort(
                      e.target.value === "recommended" ? "recommended" : "marketplace",
                    )
                  }
                >
                  <option value="marketplace">Marketplace</option>
                  <option value="recommended">Recommended</option>
                </select>
                {categoryFilter || locationFilter ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setCategoryFilter(null);
                      setLocationFilter(null);
                      setDirectoryExpanded(false);
                    }}
                  >
                    Clear filters
                  </Button>
                ) : null}
              </div>
            }
          />
          {sortRecommended && !user ? (
            <p className="text-sm text-muted-foreground">
              Sign in to sort the directory by personalized recommendations. Showing
              the global marketplace order for now.
            </p>
          ) : null}
          {sortRecommended && user && recRank.size === 0 ? (
            <p className="text-sm text-muted-foreground">
              Personalized order loads when you’re signed in. Filters still apply.
            </p>
          ) : null}
          {directory.length === 0 ? (
            <Card padded className="space-y-3">
              <p className="text-base font-extrabold text-foreground">
                No hosts match these filters
              </p>
              <p className="text-sm text-muted-foreground">
                Try another scene or city, or clear filters to see the full
                directory.
              </p>
              <Button
                variant="secondary"
                onClick={() => {
                  setCategoryFilter(null);
                  setLocationFilter(null);
                }}
              >
                Clear filters
              </Button>
            </Card>
          ) : (
            <>
              <div className="grid auto-rows-fr gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {directoryVisible.map((host, index) => (
                  <div
                    key={`dir-${host.host_id}`}
                    className={
                      !directoryExpanded && index >= DIRECTORY_MOBILE
                        ? "hidden sm:block"
                        : undefined
                    }
                  >
                    <HostMarketplaceCard
                      variant="directory"
                      host={host}
                      initiallyFollowing={hostIsFollowed(host)}
                    />
                  </div>
                ))}
              </div>
              {directoryCanExpand &&
              (directory.length > DIRECTORY_DESKTOP ||
                directory.length > DIRECTORY_MOBILE) ? (
                <div className="flex justify-center">
                  <Button
                    type="button"
                    variant="secondary"
                    size="md"
                    onClick={() => setDirectoryExpanded((v) => !v)}
                  >
                    {directoryExpanded
                      ? "Show less"
                      : `Show more (${Math.max(
                          0,
                          directory.length - DIRECTORY_MOBILE,
                        )} more)`}
                  </Button>
                </div>
              ) : null}
            </>
          )}
        </section>

        <section className="space-y-4">
          <SectionHeader
            eyebrow="Why follow"
            title="Why follow hosts on Pàdéyá"
            description="Following is how you stay close to creators beyond a single night."
          />
          <div className="grid gap-3 sm:grid-cols-2 sm:gap-4">
            {WHY_FOLLOW.map((item) => (
              <Card key={item.title} padded className="space-y-2">
                <h3 className="text-base font-extrabold text-foreground sm:text-lg">
                  {item.title}
                </h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {item.body}
                </p>
              </Card>
            ))}
          </div>
        </section>
      </Container>

      <CTASection
        tone="accent"
        title="Ready to build your own Legacy?"
        description="Create events, sell tickets, collect verified reviews, and grow an audience that follows you beyond one night."
        actions={
          <Link href="/host/onboarding">
            <Button size="lg" variant="primary">
              Start host onboarding
            </Button>
          </Link>
        }
      />
    </main>
  );
}

export function HostsMarketplace({
  initialHosts = [],
}: {
  initialHosts?: HostDiscovery[];
}) {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-background">
          <Container className="py-16 text-sm text-muted-foreground">
            Loading hosts…
          </Container>
        </main>
      }
    >
      <HostsMarketplaceInner initialHosts={initialHosts} />
    </Suspense>
  );
}
