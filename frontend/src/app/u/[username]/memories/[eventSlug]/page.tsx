"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

import { Container, SkeletonLoader } from "@/components/ui";
import { fetchPublicMemory } from "@/lib/memories-api";

/** Legacy share URL → canonical /events/{slug}/memories */
export default function LegacyPublicMemoryRedirectPage() {
  const params = useParams<{ username: string; eventSlug: string }>();
  const router = useRouter();
  const username = decodeURIComponent(params.username);
  const eventSlug = decodeURIComponent(params.eventSlug);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchPublicMemory(username, eventSlug);
        if (!active) return;
        router.replace(
          data.memories_path || `/events/${data.event_slug}/memories`,
        );
      } catch {
        if (active) router.replace(`/events/${eventSlug}/memories`);
      }
    })();
    return () => {
      active = false;
    };
  }, [username, eventSlug, router]);

  return (
    <Container className="py-16">
      <SkeletonLoader />
    </Container>
  );
}
