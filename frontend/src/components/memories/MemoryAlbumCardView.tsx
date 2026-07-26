import Link from "next/link";

import { Media } from "@/components/ui";
import type { MemoryAlbumCard } from "@/lib/types/memories";

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function MemoryAlbumCardView({ album }: { album: MemoryAlbumCard }) {
  const cover = album.cover_thumbnail_url || album.cover_url;
  const count = album.counts?.memory_count ?? 0;
  return (
    <Link
      href={album.memories_path || `/events/${album.event_slug}/memories`}
      className="group block overflow-hidden rounded-2xl border border-border bg-card transition-colors hover:border-border-strong"
    >
      <div className="relative aspect-[4/3] bg-surface-muted">
        {cover ? (
          <Media
            src={cover}
            alt=""
            fill
            className="object-cover transition-transform duration-500 group-hover:scale-[1.02]"
            sizes="(max-width: 640px) 100vw, 33vw"
          />
        ) : null}
      </div>
      <div className="space-y-1 p-4">
        <h3 className="line-clamp-2 text-base font-extrabold tracking-tight text-foreground">
          {album.event_title}
        </h3>
        <p className="text-sm text-muted-foreground">
          {formatDate(album.start_datetime)}
          {album.city ? ` · ${album.city}` : ""}
        </p>
        <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
          {count} {count === 1 ? "memory" : "memories"}
          {album.counts?.contributor_count
            ? ` · ${album.counts.contributor_count} contributors`
            : ""}
        </p>
        <p className="pt-1 text-sm font-semibold text-primary-text">
          View memories →
        </p>
      </div>
    </Link>
  );
}
