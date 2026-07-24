"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { FanConnectCard } from "@/components/fan-connect/FanConnectCard";
import {
  Alert,
  Button,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { trackFanConnectPageView } from "@/lib/analytics";
import { brand } from "@/lib/brand";
import {
  fetchConnectRequests,
  fetchConnections,
  fetchConnectSuggestions,
  fetchFanConnectSettings,
} from "@/lib/fan-connect-api";
import type {
  FanConnectSettings,
  FanConnectSuggestion,
  FanConnection,
} from "@/lib/types/fan-connect";

function hasEventSignal(s: FanConnectSuggestion): boolean {
  if ((s.shared_context?.events?.length ?? 0) > 0) return true;
  return Boolean(
    s.reasons?.some((r) =>
      [
        "shared_upcoming_event",
        "shared_public_event",
        "shared_checked_in",
      ].includes(r.code),
    ),
  );
}

function hasHostSignal(s: FanConnectSuggestion): boolean {
  if ((s.shared_context?.hosts?.length ?? 0) > 0) return true;
  return Boolean(
    s.reasons?.some((r) =>
      ["shared_host", "shared_hosts"].includes(r.code),
    ),
  );
}

function hasSceneSignal(s: FanConnectSuggestion): boolean {
  if ((s.shared_context?.categories?.length ?? 0) > 0) return true;
  return Boolean(
    s.reasons?.some((r) =>
      ["shared_category", "shared_badge"].includes(r.code),
    ),
  );
}

function partitionSuggestions(items: FanConnectSuggestion[]) {
  /** Sections can overlap — a fan may appear in Shared nights and Host circle. */
  const sameEvents = items.filter(hasEventSignal);
  const sameHosts = items.filter(hasHostSignal);
  const similarScenes = items.filter(
    (s) => hasSceneSignal(s) || (!hasEventSignal(s) && !hasHostSignal(s)),
  );
  return { sameEvents, sameHosts, similarScenes };
}

function Section({
  eyebrow,
  title,
  description,
  children,
  href,
  linkLabel,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
  empty?: boolean;
  href?: string;
  linkLabel?: string;
}) {
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="max-w-xl space-y-1">
          <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-primary">
            {eyebrow}
          </p>
          <h2 className="text-xl font-extrabold tracking-tight text-heading sm:text-2xl">
            {title}
          </h2>
          <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
        </div>
        {href && linkLabel ? (
          <Link
            href={href}
            className="text-sm font-semibold text-primary hover:underline"
          >
            {linkLabel}
          </Link>
        ) : null}
      </div>
      {children}
    </section>
  );
}

export function ConnectHome() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<FanConnectSettings | null>(null);
  const [suggestions, setSuggestions] = useState<FanConnectSuggestion[]>([]);
  const [incoming, setIncoming] = useState<FanConnection[]>([]);
  const [connections, setConnections] = useState<FanConnection[]>([]);
  const [tick, setTick] = useState(0);

  const reload = useCallback(() => setTick((n) => n + 1), []);

  useEffect(() => {
    trackFanConnectPageView({ path: "/connect" });
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [s, sugMixed, sugInterests, inReq, conns] = await Promise.all([
          fetchFanConnectSettings(),
          fetchConnectSuggestions({ limit: 24, mode: "mixed" }),
          fetchConnectSuggestions({ limit: 12, mode: "same_interests" }),
          fetchConnectRequests("incoming"),
          fetchConnections(),
        ]);
        if (!active) return;
        setSettings(s);
        const byUser = new Map<string, FanConnectSuggestion>();
        for (const item of [...sugMixed.items, ...sugInterests.items]) {
          if (item.username && !byUser.has(item.username)) {
            byUser.set(item.username, item);
          }
        }
        setSuggestions(Array.from(byUser.values()));
        setIncoming(inReq.items);
        setConnections(conns.items);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError
            ? err.detail
            : "Could not load Fan Connect.",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [tick]);

  if (loading) return <SkeletonLoader className="h-64" />;
  if (error) return <Alert tone="danger">{error}</Alert>;

  const enabled = Boolean(settings?.fan_connect_enabled);
  const { sameEvents, sameHosts, similarScenes } =
    partitionSuggestions(suggestions);

  return (
    <div className="space-y-12 sm:space-y-14">
      {/* Hero — one composition */}
      <section className="relative overflow-hidden rounded-[var(--radius-xl)] bg-ink text-paper">
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            background:
              "radial-gradient(ellipse 80% 60% at 70% 20%, color-mix(in srgb, var(--primary) 55%, transparent), transparent 55%), linear-gradient(135deg, #111 0%, #000 55%)",
          }}
        />
        <div className="relative grid gap-8 px-6 py-10 sm:px-8 sm:py-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:gap-10">
          <div className="space-y-5">
            <Image
              src={brand.logos.dark}
              alt={brand.name}
              width={160}
              height={40}
              className="h-9 w-auto"
              priority
            />
            <p className="text-[10px] font-extrabold uppercase tracking-[0.18em] text-primary">
              Fan Connect
            </p>
            <h1 className="max-w-xl text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-[2.75rem] lg:leading-[1.1]">
              Meet Explorers going where you’re going.
            </h1>
            <p className="max-w-lg text-sm leading-relaxed text-paper/75 sm:text-base">
              Connect with people attending the same events, following the same
              hosts, and building their Pàdéyá Passport — without sharing phone
              numbers or private details.
            </p>
            <div className="flex flex-wrap gap-2">
              {enabled ? (
                <Link href="/connect/suggestions">
                  <Button size="lg">Build your Pàdéyá circle</Button>
                </Link>
              ) : (
                <Link href="/connect/settings">
                  <Button size="lg">Turn on Fan Connect</Button>
                </Link>
              )}
              <Link href="/connect/settings">
                <Button size="lg" variant="outline-dark">
                  Privacy settings
                </Button>
              </Link>
            </div>
          </div>
          <div className="relative hidden min-h-[220px] overflow-hidden rounded-[var(--radius-lg)] lg:block">
            <Image
              src={brand.heroImage}
              alt=""
              fill
              className="object-cover"
              sizes="(min-width: 1024px) 40vw, 0px"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-t from-ink/80 via-ink/20 to-transparent" />
            <p className="absolute bottom-4 left-4 right-4 text-sm font-semibold text-paper">
              Shared event energy — stay on Pàdéyá.
            </p>
          </div>
        </div>
      </section>

      {!enabled ? (
        <EmptyState
          title="Fan Connect is off"
          description="Turn it on to see fans going to the same events and build your Pàdéyá circle — private by default."
          action={
            <Link href="/connect/settings">
              <Button>Open settings</Button>
            </Link>
          }
        />
      ) : (
        <>
          <Section
            eyebrow="Shared nights"
            title="Going to the same events"
            description="Fans with shared public upcoming nights or verified check-ins — never a private attendee list."
            href="/connect/events"
            linkLabel="Browse your nights →"
            empty={sameEvents.length === 0}
          >
            {sameEvents.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No shared public nights yet. Attend listed events and keep Connect
                discoverable.
              </p>
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {sameEvents.slice(0, 6).map((s) => (
                  <li key={s.username}>
                    <FanConnectCard
                      displayName={s.display_name}
                      username={s.username}
                      avatarUrl={s.avatar_url}
                      tagline={s.tagline}
                      publicCity={s.public_city}
                      badges={s.badges}
                      matchLabel={s.match_label || s.recommendation_label}
                      reasons={s.reasons}
                      sharedContext={s.shared_context}
                      cta="connect"
                      scoreBand={s.score_band}
                      listContext="fan_connect_same_events"
                      trackSuggestionAnalytics
                      contextEventId={
                        s.shared_context.events[0]?.event_id || null
                      }
                      onChanged={reload}
                    />
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section
            eyebrow="Host circle"
            title="Members who follow your hosts"
            description="People following the same public hosts you do — opt-in only."
            href="/connect/suggestions"
            linkLabel="More suggestions →"
            empty={sameHosts.length === 0}
          >
            {sameHosts.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Follow hosts you love, and other opted-in fans may appear here.
              </p>
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {sameHosts.slice(0, 6).map((s) => (
                  <li key={s.username}>
                    <FanConnectCard
                      displayName={s.display_name}
                      username={s.username}
                      avatarUrl={s.avatar_url}
                      tagline={s.tagline}
                      publicCity={s.public_city}
                      badges={s.badges}
                      matchLabel={s.match_label || s.recommendation_label}
                      reasons={s.reasons}
                      sharedContext={s.shared_context}
                      cta="connect"
                      scoreBand={s.score_band}
                      listContext="fan_connect_same_hosts"
                      trackSuggestionAnalytics
                      onChanged={reload}
                    />
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section
            eyebrow="Scenes"
            title="Similar scenes"
            description="Shared categories and public Passport energy — build your Pàdéyá circle."
            empty={similarScenes.length === 0}
          >
            {similarScenes.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Add favorite categories on your Passport to surface similar scenes.
              </p>
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {similarScenes.slice(0, 6).map((s) => (
                  <li key={s.username}>
                    <FanConnectCard
                      displayName={s.display_name}
                      username={s.username}
                      avatarUrl={s.avatar_url}
                      tagline={s.tagline}
                      publicCity={s.public_city}
                      badges={s.badges}
                      matchLabel={s.match_label || s.recommendation_label}
                      reasons={s.reasons}
                      sharedContext={s.shared_context}
                      cta="connect"
                      scoreBand={s.score_band}
                      listContext="fan_connect_scenes"
                      trackSuggestionAnalytics
                      onChanged={reload}
                    />
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section
            eyebrow="Inbox"
            title="Requests"
            description="Accept only when you’re ready — chat unlocks after both say yes."
            href="/connect/requests"
            linkLabel="All requests →"
            empty={incoming.length === 0}
          >
            {incoming.length === 0 ? (
              <p className="text-sm text-muted-foreground">No incoming requests right now.</p>
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {incoming.slice(0, 6).map((row) => {
                  const uname = row.counterpart.username;
                  if (!uname) return null;
                  return (
                    <li key={row.id}>
                      <FanConnectCard
                        displayName={row.counterpart.display_name}
                        username={uname}
                        avatarUrl={row.counterpart.avatar_url}
                        tagline={row.counterpart.tagline}
                        matchLabel="Incoming request"
                        reasons={row.reasons}
                        sharedContext={row.shared_context}
                        cta="accept"
                        connectionId={row.id}
                        onChanged={reload}
                      />
                    </li>
                  );
                })}
              </ul>
            )}
          </Section>

          <Section
            eyebrow="Your circle"
            title="Connections"
            description="Accepted Fan Connect pairs — message in-app, no phone numbers."
            href="/connect/connections"
            linkLabel="All connections →"
            empty={connections.length === 0}
          >
            {connections.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                When you accept a request, connections show up here.
              </p>
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {connections.slice(0, 6).map((row) => {
                  const uname = row.counterpart.username;
                  if (!uname) return null;
                  return (
                    <li key={row.id}>
                      <FanConnectCard
                        displayName={row.counterpart.display_name}
                        username={uname}
                        avatarUrl={row.counterpart.avatar_url}
                        tagline={row.counterpart.tagline}
                        matchLabel="Connected"
                        reasons={row.reasons}
                        sharedContext={row.shared_context}
                        cta="message"
                        threadId={row.thread_id}
                        connectionId={row.id}
                        onChanged={reload}
                      />
                    </li>
                  );
                })}
              </ul>
            )}
          </Section>
        </>
      )}

      <section className="rounded-[var(--radius-lg)] border border-border bg-surface-muted/60 px-5 py-6 sm:px-6">
        <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-primary">
          Privacy
        </p>
        <h2 className="mt-2 text-lg font-extrabold text-heading">
          Privacy reminder
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Fan Connect never shows private attendance, hidden venues, ticket
          types, or spend. Phone numbers and emails stay off the chat. Keep
          conversations on Pàdéyá — and only connect when the shared public
          reason feels right.
        </p>
        <div className="mt-4">
          <Link href="/connect/settings">
            <Button size="sm" variant="secondary">
              Review Connect settings
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
