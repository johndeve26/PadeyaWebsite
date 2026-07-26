"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button, Media } from "@/components/ui";
import { fetchMemoryByEventSlug } from "@/lib/memories-api";
import type { EventMemory } from "@/lib/types/memories";

export function EventMemoriesPreview({
  eventSlug,
  eventTitle,
}: {
  eventSlug: string;
  eventTitle: string;
}) {
  const [memory, setMemory] = useState<EventMemory | null>(null);

  useEffect(() => {
    let active = true;
    void fetchMemoryByEventSlug(eventSlug)
      .then((data) => {
        if (active) setMemory(data);
      })
      .catch(() => {
        if (active) setMemory(null);
      });
    return () => {
      active = false;
    };
  }, [eventSlug]);

  const photos = (memory?.media ?? []).slice(0, 4);
  const count = memory?.counts?.memory_count ?? photos.length;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-extrabold tracking-tight text-foreground">
            Memories
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {count > 0
              ? `${count} memories from the host and verified attendees`
              : "Relive this night with photos from the host and verified attendees."}
          </p>
        </div>
        <Link href={`/events/${eventSlug}/memories`}>
          <Button type="button">Explore all memories</Button>
        </Link>
      </div>
      {photos.length > 0 ? (
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {photos.map((photo) => (
            <li
              key={photo.id}
              className="relative aspect-square overflow-hidden rounded-xl bg-surface-muted"
            >
              <Media
                src={photo.thumbnail_url || photo.url}
                alt=""
                fill
                className="object-cover"
                sizes="25vw"
              />
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">
          Be the first to explore the {eventTitle} album.
        </p>
      )}
    </section>
  );
}
