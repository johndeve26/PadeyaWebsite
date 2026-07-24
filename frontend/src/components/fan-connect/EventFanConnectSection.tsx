"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { FanConnectCard } from "@/components/fan-connect/FanConnectCard";
import { suggestionCta } from "@/lib/fan-connect-suggestion-cta";
import { Button } from "@/components/ui";
import { useHostAffiliation } from "@/hooks/useHostAffiliation";
import {
  fetchConnectSuggestions,
  fetchFanConnectSettings,
} from "@/lib/fan-connect-api";
import type { FanConnectSuggestion } from "@/lib/types/fan-connect";
import type { EventItem } from "@/lib/types/events";

const PREVIEW_LIMIT = 3;

/** Public-safe event check mirroring passport privacy rules (client gate). */
export function eventIsPublicSafeForConnect(
  event: Pick<EventItem, "visibility" | "event_type" | "status">,
): boolean {
  const visibility = (event.visibility || "listed").toLowerCase();
  const eventType = (event.event_type || "public").toLowerCase();
  const status = (event.status || "").toLowerCase();
  if (visibility !== "listed") return false;
  if (["secret_location", "invite_only", "private"].includes(eventType)) {
    return false;
  }
  if (!["published", "completed", "ended"].includes(status)) return false;
  return true;
}

type Props = {
  event: EventItem;
  previewMode?: boolean;
};

type LoadState =
  | { kind: "loading" }
  | { kind: "hidden" }
  | { kind: "enable" }
  | { kind: "ready"; items: FanConnectSuggestion[] };

/**
 * Optional event detail block — never a full attendee list, ticket counts,
 * VIP/table buyers, or private profiles. Public-safe events + opted-in fans only.
 */
export function EventFanConnectSection({ event, previewMode = false }: Props) {
  const { user } = useAuth();
  const { affiliated: isOwnHost } = useHostAffiliation({
    hostId: event.host_id,
    hostSlug: event.host_slug,
  });
  const publicSafe = eventIsPublicSafeForConnect(event);
  // Private/hidden events, host preview, own-host owner, and logged-out: never show.
  const gatedOut = !publicSafe || previewMode || !user || isOwnHost;
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    if (gatedOut) return;

    let active = true;
    void (async () => {
      try {
        const settings = await fetchFanConnectSettings();
        if (!active) return;
        if (!settings.fan_connect_enabled) {
          setState({ kind: "enable" });
          return;
        }
        const sug = await fetchConnectSuggestions({
          eventId: event.id,
          limit: PREVIEW_LIMIT,
        });
        if (!active) return;
        setState({ kind: "ready", items: sug.items.slice(0, PREVIEW_LIMIT) });
      } catch {
        if (active) setState({ kind: "hidden" });
      }
    })();

    return () => {
      active = false;
    };
  }, [gatedOut, event.id]);

  if (gatedOut || state.kind === "loading" || state.kind === "hidden") {
    return null;
  }

  if (state.kind === "enable") {
    return (
      <section className="border-t border-border px-1 py-6 sm:px-0">
        <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-primary">
          Fan Connect
        </p>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
          Enable Fan Connect to meet fans going where you’re going.
        </p>
        <div className="mt-3">
          <Link href="/connect/settings">
            <Button size="sm" variant="secondary">
              Enable Fan Connect
            </Button>
          </Link>
        </div>
      </section>
    );
  }

  const items = state.items;
  const connectHref = `/connect/suggestions?event=${encodeURIComponent(event.id)}`;

  return (
    <section className="rounded-[var(--radius-xl)] border border-border bg-card px-5 py-6 shadow-[var(--shadow-soft)] dark:bg-surface-elevated dark:shadow-[var(--shadow)] sm:px-6">
      <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-primary">
        Fan Connect
      </p>
      <h2 className="mt-2 text-xl font-extrabold tracking-tight text-heading sm:text-2xl">
        Going too? Connect with fans.
      </h2>
      <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
        Find fans who opted in to connect around this event.
      </p>

      {items.length > 0 ? (
        <ul className="mt-5 grid gap-3 sm:grid-cols-3">
          {items.map((s) => (
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
                cta={suggestionCta(s)}
                cooldownUntil={s.cooldown_until}
                viewerDeclinedTarget={s.viewer_declined_target}
                scoreBand={s.score_band}
                listContext="event_fan_connect"
                trackSuggestionAnalytics
                contextEventId={event.id}
              />
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground">
          No opted-in fans to preview yet — open Fan Connect to see who shares
          this public night.
        </p>
      )}

      <div className="mt-5">
        <Link href={connectHref}>
          <Button size="sm">View Fan Connect</Button>
        </Link>
      </div>
    </section>
  );
}
