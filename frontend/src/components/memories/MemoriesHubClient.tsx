"use client";

import Link from "next/link";
import { useEffect } from "react";

import { MemoryAlbumCardView } from "@/components/memories/MemoryAlbumCardView";
import { Container, SectionHeader } from "@/components/ui";
import { track } from "@/lib/analytics";
import { TrackedAction } from "@/lib/analytics-taxonomy";
import type { MemoryAlbumCard } from "@/lib/types/memories";

export function MemoriesHubClient({ albums }: { albums: MemoryAlbumCard[] }) {
  useEffect(() => {
    track(TrackedAction.MEMORIES_PAGE_VIEW, {});
  }, []);

  return (
    <Container className="py-10 sm:py-14">
      <SectionHeader
        eyebrow="Memories"
        title="Relive the nights that brought people together."
        description="Event albums shared by hosts and verified attendees — after the night ends."
      />

      <div className="mt-8 flex flex-wrap gap-3 text-sm">
        <Link
          href="/events"
          className="font-semibold text-primary-text underline-offset-4 hover:underline"
        >
          Browse upcoming events
        </Link>
      </div>

      <section className="mt-10 space-y-4">
        <h2 className="text-lg font-extrabold tracking-tight text-foreground">
          Recent Memories
        </h2>
        {albums.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No public memory albums yet. Completed events with photos will appear here.
          </p>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {albums.map((album) => (
              <li key={album.event_id}>
                <MemoryAlbumCardView album={album} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </Container>
  );
}
