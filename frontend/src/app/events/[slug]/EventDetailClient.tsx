"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EventPublicView } from "@/components/events/EventPublicView";
import { EventUnavailableState } from "@/components/not-found/EventUnavailableState";
import { useAuth } from "@/components/auth/AuthProvider";
import { Container, SkeletonCard } from "@/components/ui";
import {
  captureAmbassadorReferral,
  readAmbassadorCodeFromSearchParams,
} from "@/lib/ambassador-referral";
import { fetchPublicEvent, fetchPublicEvents } from "@/lib/events-api";
import { trackAmbassadorReferralLanding } from "@/lib/referral-click-track";
import type { EventItem } from "@/lib/types/events";

function applyReferral(
  event: EventItem,
  slug: string,
  referralCode: string | null,
) {
  if (!referralCode) return;
  captureAmbassadorReferral(slug, referralCode);
  captureAmbassadorReferral(event.id, referralCode);
  void trackAmbassadorReferralLanding({
    referral_code: referralCode,
    event_id: event.id,
    landing_path: `/events/${slug}?ref=${referralCode}`,
    source: "event_page",
  });
}

/** Related rail: category-scoped list instead of the full marketplace dump. */
async function loadRelated(event: EventItem): Promise<EventItem[]> {
  const category = event.category?.slug;
  try {
    const rows = await fetchPublicEvents(
      category ? { category, sort: "soonest" } : { sort: "soonest" },
    );
    return rows.filter((e) => e.id !== event.id).slice(0, 24);
  } catch {
    return [];
  }
}

export function EventDetailClient({
  initialEvent = null,
}: {
  /** Server-fetched event — avoids a duplicate public detail request. */
  initialEvent?: EventItem | null;
}) {
  const params = useParams<{ slug: string }>();
  const searchParams = useSearchParams();
  const [event, setEvent] = useState<EventItem | null>(initialEvent);
  const [allEvents, setAllEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const referralCode = readAmbassadorCodeFromSearchParams(searchParams);
  const { user } = useAuth();

  useEffect(() => {
    let cancelled = false;
    const slug = params.slug;

    async function run() {
      try {
        let current = initialEvent;
        if (!current || current.slug !== slug) {
          current = await fetchPublicEvent(slug);
        }
        if (cancelled) return;
        setEvent(current);
        applyReferral(current, slug, referralCode);
        if (!user) {
          const related = await loadRelated(current);
          if (!cancelled) setAllEvents(related);
        } else if (!cancelled) {
          setAllEvents([]);
        }
      } catch {
        if (!cancelled) setError("unavailable");
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [params.slug, referralCode, initialEvent, user]);

  if (error) {
    return <EventUnavailableState />;
  }

  if (!event) {
    return (
      <main className="bg-background">
        <div className="h-[42vh] animate-pulse bg-surface-dark sm:h-[52vh]" />
        <Container className="grid gap-6 py-10 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-4">
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <SkeletonCard />
        </Container>
      </main>
    );
  }

  return (
    <EventPublicView
      event={event}
      related={allEvents}
      referralCode={referralCode}
    />
  );
}
