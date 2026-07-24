"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { SectionLabel } from "@/components/personal/command-center/SectionLabel";
import { Badge, Button, Card, EmptyState, SkeletonLoader } from "@/components/ui";
import {
  eventRecommendationFeedback,
  fetchEventRecommendations,
  recordEventRecommendationImpressions,
} from "@/lib/events-api";
import type { EventRecommendation } from "@/lib/types/event-recommendations";

export type EventRecommendationSurface =
  | "dashboard_events_for_you"
  | "events_recommended_rail"
  | "events_sort_recommended"
  | "event_detail_recommended";

export type EventRecommendationDetailContext = {
  excludeEventId: string;
  contextEventId?: string;
  category?: string;
  city?: string;
  area?: string;
  hostId?: string;
};

type EventRecommendationsSectionProps = {
  variant?: "rail" | "page" | "detail";
  limit?: number;
  surface?: EventRecommendationSurface;
  title?: string;
  seeAllHref?: string | null;
  detailContext?: EventRecommendationDetailContext;
};

export function EventRecommendationsSection({
  variant = "rail",
  limit = 8,
  surface = "dashboard_events_for_you",
  title,
  seeAllHref = "/events?sort=recommended",
  detailContext,
}: EventRecommendationsSectionProps) {
  const [items, setItems] = useState<EventRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [emptyCopy, setEmptyCopy] = useState<{
    title?: string | null;
    description?: string | null;
  }>({});
  const impressionsSent = useRef(false);
  const sectionRef = useRef<HTMLElement | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await fetchEventRecommendations({
        limit,
        mode: detailContext ? "recommended" : undefined,
        excludeEventId: detailContext?.excludeEventId,
        contextEventId: detailContext?.contextEventId ?? detailContext?.excludeEventId,
        category: detailContext?.category,
        city: detailContext?.city,
        area: detailContext?.area,
        hostId: detailContext?.hostId,
      });
      setItems(res.events);
      setEmptyCopy({
        title: res.empty_title,
        description: res.empty_description,
      });
    } catch {
      setError(true);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [limit, detailContext]);

  useEffect(() => {
    void load();
  }, [load]);

  const sendImpressions = useCallback(() => {
    if (items.length === 0 || impressionsSent.current) return;
    impressionsSent.current = true;
    void recordEventRecommendationImpressions(
      items.map((item, index) => ({
        event_id: item.event.id,
        surface,
        position: index,
        recommendation_score: item.score,
        reason_codes: item.reasons.map((r) => r.code),
      })),
    ).catch(() => {
      impressionsSent.current = false;
    });
  }, [items, surface]);

  useEffect(() => {
    if (loading || items.length === 0) return;
    if (variant !== "detail") {
      sendImpressions();
      return;
    }
    const node = sectionRef.current;
    if (!node || typeof IntersectionObserver === "undefined") {
      sendImpressions();
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          sendImpressions();
          observer.disconnect();
        }
      },
      { root: null, rootMargin: "0px", threshold: 0.2 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [items, loading, variant, sendImpressions]);

  async function onDismiss(eventId: string) {
    try {
      await eventRecommendationFeedback(eventId, "dismissed");
      setItems((prev) => prev.filter((i) => i.event.id !== eventId));
    } catch {
      /* keep card */
    }
  }

  async function onNotInterested(eventId: string) {
    try {
      await eventRecommendationFeedback(eventId, "not_interested");
      setItems((prev) => prev.filter((i) => i.event.id !== eventId));
    } catch {
      /* keep card */
    }
  }

  async function onSaved(eventId: string) {
    try {
      await eventRecommendationFeedback(eventId, "saved");
    } catch {
      /* non-blocking */
    }
  }

  const railTitle = title ?? "Events for you";

  if (loading && (variant === "rail" || variant === "detail")) return null;
  if (loading && variant === "page") {
    return (
      <div className="space-y-3">
        <SkeletonLoader className="h-8 w-48" />
        <SkeletonLoader className="h-40" />
      </div>
    );
  }
  if (error && (variant === "rail" || variant === "detail")) return null;
  if (error && variant === "page") {
    return (
      <EmptyState
        title="Couldn’t load recommendations"
        description="Try again in a moment."
        action={
          <Button size="sm" onClick={() => void load()}>
            Retry
          </Button>
        }
      />
    );
  }
  if (items.length === 0 && (variant === "rail" || variant === "detail")) return null;
  if (items.length === 0 && variant === "page") {
    return (
      <EmptyState
        title={emptyCopy.title ?? "No event matches yet"}
        description={
          emptyCopy.description ??
          "Follow hosts, grab tickets, or set your city and Pàdéyá will surface nights for you."
        }
        action={
          <Link href="/events">
            <Button>Browse events</Button>
          </Link>
        }
      />
    );
  }

  const showHeader = variant === "rail" || variant === "detail";

  return (
    <section
      ref={sectionRef}
      className="min-w-0 space-y-3"
      data-surface={surface}
    >
      {showHeader ? (
        <div className="flex flex-wrap items-end justify-between gap-2">
          <SectionLabel>{railTitle}</SectionLabel>
          {seeAllHref ? (
            <Link href={seeAllHref} className="text-sm font-semibold text-primary">
              See all
            </Link>
          ) : null}
        </div>
      ) : null}
      <div
        className={
          variant === "page"
            ? "grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-3"
            : variant === "detail"
              ? "grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-3"
              : "grid min-w-0 gap-3 sm:grid-cols-2"
        }
      >
        {items.map((item) => (
          <Card key={item.event.id} className="min-w-0 space-y-3 p-4">
            <div className="min-w-0">
              <Link
                href={`/events/${item.event.slug}`}
                className="font-extrabold text-foreground hover:text-primary"
                onClick={() => void eventRecommendationFeedback(item.event.id, "clicked")}
              >
                {item.event.title}
              </Link>
              <p className="text-sm text-muted-foreground">
                {item.event.city ?? "City TBA"}
                {item.event.start_datetime
                  ? ` · ${new Date(item.event.start_datetime).toLocaleDateString()}`
                  : ""}
              </p>
            </div>
            {item.reasons.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {item.reasons.slice(0, 3).map((r) => (
                  <Badge key={r.code} tone="neutral" className="text-xs font-normal">
                    {r.label}
                  </Badge>
                ))}
              </div>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Link href={`/events/${item.event.slug}`}>
                <Button size="sm" variant="secondary">
                  View event
                </Button>
              </Link>
              <Button size="sm" variant="ghost" onClick={() => void onSaved(item.event.id)}>
                Save
              </Button>
              <Button size="sm" variant="ghost" onClick={() => void onDismiss(item.event.id)}>
                Dismiss
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => void onNotInterested(item.event.id)}
              >
                Not interested
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </section>
  );
}
