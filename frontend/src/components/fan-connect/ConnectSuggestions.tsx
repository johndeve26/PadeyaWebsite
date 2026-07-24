"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { FanConnectCard } from "@/components/fan-connect/FanConnectCard";
import { Alert, Button, EmptyState, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  dismissConnectSuggestion,
  fetchConnectSuggestions,
  moreLikeThisSuggestion,
} from "@/lib/fan-connect-api";
import { suggestionCta } from "@/lib/fan-connect-suggestion-cta";
import type {
  FanConnectSuggestion,
  FanConnectSuggestionMode,
} from "@/lib/types/fan-connect";

const TABS: { id: FanConnectSuggestionMode; label: string }[] = [
  { id: "mixed", label: "Best matches" },
  { id: "near_me", label: "Near me" },
  { id: "same_event", label: "Same event" },
  { id: "connections_of_connections", label: "Friends of friends" },
  { id: "same_interests", label: "Same interests" },
  { id: "new_people", label: "New people" },
];

function emptyCopy(
  mode: FanConnectSuggestionMode,
  fromApi?: { title?: string | null; description?: string | null },
) {
  if (fromApi?.title && fromApi?.description) {
    return { title: fromApi.title, description: fromApi.description };
  }
  switch (mode) {
    case "near_me":
      return {
        title: "No nearby fans yet",
        description:
          "Check back as more fans opt in near your city and events.",
      };
    case "connections_of_connections":
      return {
        title: "No friends-of-friends yet",
        description:
          "No friends-of-friends yet. Connect with more fans to improve this.",
      };
    case "same_interests":
      return {
        title: "No interest matches yet",
        description:
          "Add interests to your Fan Passport to get better suggestions.",
      };
    case "same_event":
      return {
        title: "No shared-event fans yet",
        description:
          "Get tickets to public nights on Pàdéyá to meet fans going too.",
      };
    case "new_people":
      return {
        title: "No new people right now",
        description:
          "Check back soon — fresh Passports appear here as fans join.",
      };
    default:
      return {
        title: "No suggestions right now",
        description:
          "Suggestions only show opted-in fans with shared event energy — never a dating feed.",
      };
  }
}

export function ConnectSuggestions() {
  const searchParams = useSearchParams();
  const eventId = searchParams.get("event") || undefined;
  const [mode, setMode] = useState<FanConnectSuggestionMode>("mixed");
  const [items, setItems] = useState<FanConnectSuggestion[]>([]);
  const [emptyMeta, setEmptyMeta] = useState<{
    title?: string | null;
    description?: string | null;
  }>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    void (async () => {
      setLoading(true);
      try {
        const data = await fetchConnectSuggestions({
          eventId,
          mode,
          limit: 24,
        });
        if (!active) return;
        setItems(data.items);
        setEmptyMeta({
          title: data.empty_title,
          description: data.empty_description,
        });
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError
            ? err.detail
            : "Could not load suggestions.",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [eventId, tick, mode]);

  async function handleDismiss(userId: string) {
    setItems((prev) => prev.filter((i) => i.user_id !== userId));
    try {
      await dismissConnectSuggestion(userId);
    } catch {
      setTick((n) => n + 1);
    }
  }

  async function handleMoreLike(userId: string) {
    try {
      await moreLikeThisSuggestion(userId);
      setTick((n) => n + 1);
    } catch {
      /* ignore — optional personalization */
    }
  }

  const empty = emptyCopy(mode, emptyMeta);

  return (
    <div className="space-y-4">
      <div
        className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        role="tablist"
        aria-label="Suggestion filters"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={mode === tab.id}
            onClick={() => setMode(tab.id)}
            className={`shrink-0 rounded-[var(--radius-md)] px-3 py-1.5 text-sm font-semibold transition ${
              mode === tab.id
                ? "bg-primary text-primary-foreground"
                : "bg-muted/60 text-foreground hover:bg-muted"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex justify-end">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={() => setTick((n) => n + 1)}
        >
          Refresh
        </Button>
      </div>

      {loading ? <SkeletonLoader className="h-28" /> : null}
      {!loading && error ? <Alert tone="danger">{error}</Alert> : null}
      {!loading && !error && items.length === 0 ? (
        <EmptyState title={empty.title} description={empty.description} />
      ) : null}
      {!loading && !error && items.length > 0 ? (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((s) => (
            <li key={s.user_id || s.username}>
              <FanConnectCard
                userId={s.user_id}
                displayName={s.display_name}
                username={s.username}
                avatarUrl={s.avatar_url}
                tagline={s.tagline}
                publicCity={s.public_city}
                badges={s.badges}
                matchLabel={s.match_label || s.recommendation_label}
                reasons={s.reasons}
                distanceLabel={s.distance_label}
                mutualConnectionCount={s.mutual_connection_count}
                sharedContext={s.shared_context}
                cta={suggestionCta(s)}
                cooldownUntil={s.cooldown_until}
                viewerDeclinedTarget={s.viewer_declined_target}
                scoreBand={s.score_band}
                listContext="fan_connect_suggestions"
                trackSuggestionAnalytics
                threadId={undefined}
                contextEventId={
                  s.shared_context.events[0]?.event_id || eventId
                }
                onDismiss={
                  s.user_id
                    ? () => void handleDismiss(s.user_id!)
                    : undefined
                }
                onMoreLikeThis={
                  s.user_id
                    ? () => void handleMoreLike(s.user_id!)
                    : undefined
                }
                onChanged={() => setTick((n) => n + 1)}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
