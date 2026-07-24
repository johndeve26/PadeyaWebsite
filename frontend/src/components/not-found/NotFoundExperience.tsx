"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Button, Input, Logo } from "@/components/ui";
import { track } from "@/lib/analytics";
import { TrackedAction } from "@/lib/analytics-taxonomy";
import { brand } from "@/lib/brand";
import { fetchPublicEvents } from "@/lib/events-api";
import { fetchDiscoverHosts } from "@/lib/hosts-api";
import {
  buildNotFoundCtas,
  classifyNotFoundPath,
  NOT_FOUND_HELP_LINKS,
  sanitizeNotFoundPath,
  sanitizeUserAgent,
} from "@/lib/not-found-helpers";
import type { EventItem } from "@/lib/types/events";

type SearchHit =
  | { kind: "event"; id: string; title: string; href: string }
  | { kind: "host"; id: string; title: string; href: string };

/**
 * Premium dark 404 recovery surface — ink background, brand green accent.
 * Lives under root `app/not-found.tsx` (real HTTP 404 + noindex).
 */
export function NotFoundExperience() {
  const pathname = usePathname() || "/";
  const router = useRouter();
  const { user, loading } = useAuth();
  const pathKind = useMemo(() => classifyNotFoundPath(pathname), [pathname]);
  const ctas = useMemo(
    () => buildNotFoundCtas(loading ? null : user, pathKind),
    [user, loading, pathKind],
  );

  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    const path = sanitizeNotFoundPath(pathname);
    let referrer: string | undefined;
    if (typeof document !== "undefined" && document.referrer) {
      try {
        referrer = sanitizeNotFoundPath(new URL(document.referrer).pathname);
      } catch {
        referrer = undefined;
      }
    }
    const ua = sanitizeUserAgent(
      typeof navigator !== "undefined" ? navigator.userAgent : null,
    );
    track(TrackedAction.NOT_FOUND_VIEW, {
      immediate: true,
      metadata: {
        path,
        path_kind: pathKind,
        ...(referrer ? { referrer_path: referrer } : {}),
        ...(ua ? { user_agent: ua } : {}),
        logged_in: Boolean(user),
      },
    });
  }, [pathname, pathKind, user]);

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (q.length < 2) {
      setSearchError("Enter at least 2 characters.");
      return;
    }
    setSearching(true);
    setSearchError(null);
    try {
      const [events, hosts] = await Promise.all([
        fetchPublicEvents({ q }).catch(() => [] as EventItem[]),
        fetchDiscoverHosts().catch(() => []),
      ]);
      const eventHits: SearchHit[] = events.slice(0, 5).map((ev) => ({
        kind: "event",
        id: ev.id,
        title: ev.title,
        href: `/events/${ev.slug}`,
      }));
      const qLower = q.toLowerCase();
      const hostHits: SearchHit[] = hosts
        .filter((h) => {
          const name = (h.display_name || "").toLowerCase();
          const slug = (h.username || "").toLowerCase();
          return name.includes(qLower) || slug.includes(qLower);
        })
        .slice(0, 5)
        .map((h) => ({
          kind: "host" as const,
          id: h.host_id,
          title: h.display_name || h.username || "Host",
          href: h.share_path || `/@${h.username}`,
        }));
      const merged = [...eventHits, ...hostHits];
      setHits(merged);
      if (!merged.length) {
        setSearchError("No matching events or hosts. Try Explore events.");
      }
      track(TrackedAction.EVENT_SEARCH_PERFORMED, {
        metadata: {
          list_context: "not_found_recovery",
          q_length: q.length,
          result_count: merged.length,
        },
      });
    } catch {
      setSearchError("Search is temporarily unavailable.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <main className="relative flex min-h-[75vh] flex-col overflow-hidden bg-ink text-paper">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_55%_at_50%_-10%,color-mix(in_srgb,#8EF012_22%,transparent),transparent_55%)]"
      />
      <div className="relative mx-auto flex w-full max-w-xl flex-1 flex-col px-6 py-16 sm:py-20">
        <div className="flex justify-center">
          <Logo variant="dark" height={40} href="/" />
        </div>

        <p
          className="mt-10 text-center font-display text-6xl font-extrabold tracking-tight sm:text-7xl"
          style={{ color: brand.colors.green }}
          aria-hidden
        >
          404
        </p>

        <h1 className="mt-4 text-center font-display text-3xl font-extrabold tracking-tight text-paper sm:text-4xl">
          Page not found
        </h1>
        <p className="mt-3 text-center text-base leading-relaxed text-paper/70 sm:text-lg">
          The page you’re looking for may have moved, expired, or no longer
          exists.
        </p>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:justify-center">
          {ctas.map((cta) => (
            <Link key={`${cta.href}-${cta.label}`} href={cta.href} className="w-full sm:w-auto">
              <Button
                size="lg"
                variant={cta.variant === "primary" ? "primary" : "outline-dark"}
                className="w-full sm:w-auto"
              >
                {cta.label}
              </Button>
            </Link>
          ))}
        </div>

        <form
          onSubmit={(e) => void onSearch(e)}
          className="mt-10 space-y-3 rounded-[var(--radius-lg)] border border-paper/15 bg-paper/5 p-4 sm:p-5"
        >
          <label className="block text-left text-sm font-semibold text-paper">
            Search events & hosts
          </label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Try an event name or host…"
              className="border-paper/20 bg-ink text-paper placeholder:text-paper/40"
              aria-label="Search events and hosts"
            />
            <Button
              type="submit"
              size="md"
              disabled={searching}
              className="shrink-0"
            >
              {searching ? "Searching…" : "Search"}
            </Button>
          </div>
          {searchError ? (
            <p className="text-sm text-paper/60" role="status">
              {searchError}
            </p>
          ) : null}
          {hits.length ? (
            <ul className="divide-y divide-paper/10 text-left text-sm">
              {hits.map((hit) => (
                <li key={`${hit.kind}-${hit.id}`}>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-3 py-2.5 text-left text-paper hover:text-primary"
                    onClick={() => router.push(hit.href)}
                  >
                    <span className="font-medium">{hit.title}</span>
                    <span className="text-xs uppercase tracking-wide text-paper/45">
                      {hit.kind}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </form>

        <nav
          aria-label="Helpful links"
          className="mt-10 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm"
        >
          {NOT_FOUND_HELP_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="font-semibold text-paper/70 underline-offset-4 hover:text-primary hover:underline"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <p className="mt-8 text-center text-xs text-paper/40">
          {brand.name} · still here for the night
        </p>
      </div>
    </main>
  );
}
