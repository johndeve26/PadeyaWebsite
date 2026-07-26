"use client";

import Link from "next/link";
import { useMemo } from "react";

import { ExternalGalleryLink } from "@/components/memories/ExternalGalleryLink";
import { FanMemoryUploadCard } from "@/components/memories/FanMemoryUploadCard";
import { HostFollowControls } from "@/components/hosts/HostFollowControls";
import { Button, Media } from "@/components/ui";
import { cn } from "@/lib/cn";
import { memoriesHref, pickMemoryPreviewPhotos } from "@/lib/events/completed-event";
import type { EventItem } from "@/lib/types/events";
import type { EventMemory, MemoryMedia } from "@/lib/types/memories";

type CompletedEventMemoriesPreviewProps = {
  event: EventItem;
  memory: EventMemory | null;
  loading?: boolean;
  previewMode?: boolean;
  isOwnHost?: boolean;
};

function Collage({ photos, eventTitle }: { photos: MemoryMedia[]; eventTitle: string }) {
  const items = pickMemoryPreviewPhotos(photos, 3);
  if (items.length === 1) {
    const photo = items[0];
    return (
      <div className="relative aspect-[16/10] overflow-hidden rounded-2xl bg-surface-muted">
        <Media
          src={photo.thumbnail_url || photo.url}
          alt={photo.caption || `${eventTitle} memory`}
          fill
          className="object-cover"
          sizes="(max-width: 1024px) 100vw, 70vw"
          priority
        />
      </div>
    );
  }
  if (items.length === 2) {
    return (
      <ul className="grid grid-cols-2 gap-2">
        {items.map((photo, i) => (
          <li
            key={photo.id}
            className="relative aspect-[4/3] overflow-hidden rounded-2xl bg-surface-muted"
          >
            <Media
              src={photo.thumbnail_url || photo.url}
              alt={photo.caption || `${eventTitle} memory`}
              fill
              className="object-cover"
              sizes="(max-width: 640px) 50vw, 35vw"
              priority={i === 0}
              loading={i === 0 ? "eager" : "lazy"}
            />
          </li>
        ))}
      </ul>
    );
  }
  const [cover, a, b] = items;
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
      <div className="relative aspect-[4/3] overflow-hidden rounded-2xl bg-surface-muted sm:aspect-auto sm:min-h-[280px]">
        <Media
          src={cover.thumbnail_url || cover.url}
          alt={cover.caption || `${eventTitle} cover memory`}
          fill
          className="object-cover"
          sizes="(max-width: 640px) 100vw, 45vw"
          priority
        />
      </div>
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-1 sm:grid-rows-2">
        {[a, b].map((photo) => (
          <li
            key={photo.id}
            className="relative aspect-[4/3] overflow-hidden rounded-2xl bg-surface-muted sm:aspect-auto sm:min-h-[136px]"
          >
            <Media
              src={photo.thumbnail_url || photo.url}
              alt={photo.caption || `${eventTitle} memory`}
              fill
              className="object-cover"
              sizes="(max-width: 640px) 50vw, 25vw"
              loading="lazy"
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CompletedEventMemoriesPreview({
  event,
  memory,
  loading = false,
  previewMode = false,
  isOwnHost = false,
}: CompletedEventMemoriesPreviewProps) {
  const photos = useMemo(() => {
    if (!memory) return [] as MemoryMedia[];
    const host = memory.host_media?.length
      ? memory.host_media
      : memory.media.filter((m) => (m.uploader_role || "host") === "host");
    const community = memory.community_media?.length
      ? memory.community_media
      : memory.media.filter((m) => m.uploader_role === "fan");
    return [...host, ...community];
  }, [memory]);

  const count = memory?.counts?.memory_count ?? photos.length;
  const path = memoriesHref(event.slug);

  return (
    <section className="space-y-5" aria-labelledby="completed-memories-heading">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="max-w-2xl">
          <h2
            id="completed-memories-heading"
            className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl"
          >
            Memories
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground sm:text-base">
            Relive {event.title} through photos shared by the host and verified
            attendees.
          </p>
        </div>
        {count > 0 ? (
          <Link href={path}>
            <Button type="button">Explore all memories</Button>
          </Link>
        ) : null}
      </div>

      {loading ? (
        <div
          className="min-h-[220px] animate-pulse rounded-2xl bg-surface-inset"
          aria-hidden
        />
      ) : photos.length > 0 ? (
        <>
          <Collage photos={photos} eventTitle={event.title} />
          <p className="text-sm text-muted-foreground">
            <span className="font-extrabold text-foreground">{count}</span>{" "}
            {count === 1 ? "memory" : "memories"}
            {" · "}
            Host + verified attendees
          </p>
        </>
      ) : (
        <div
          className={cn(
            "rounded-2xl border border-border bg-card px-5 py-8 text-center dark:bg-surface-elevated",
          )}
        >
          <p className="text-base font-semibold text-foreground">
            No memories have been shared from this event yet.
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            {isOwnHost
              ? "Add the first host photos from your dashboard."
              : "Verified attendees can share up to 5 photos once they open the album."}
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <Link href={path}>
              <Button type="button" variant="secondary">
                Open album
              </Button>
            </Link>
            {!previewMode && event.host_id && !isOwnHost ? (
              <HostFollowControls
                hostId={event.host_id}
                hostSlug={event.host_slug || undefined}
                hostDisplayName={event.host_display_name || "Host"}
                loginNextPath={`/events/${event.slug}`}
                size="md"
              />
            ) : null}
          </div>
        </div>
      )}

      {!previewMode ? (
        <FanMemoryUploadCard
          eventId={event.id}
          eventSlug={event.slug}
          eventTitle={event.title}
        />
      ) : null}

      {memory?.external_gallery_url ? (
        <ExternalGalleryLink
          url={memory.external_gallery_url}
          label={memory.external_gallery_label}
          eventId={event.id}
          eventTitle={event.title}
        />
      ) : null}
    </section>
  );
}
