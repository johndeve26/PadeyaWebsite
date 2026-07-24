import Link from "next/link";

import { Media } from "@/components/ui";
import type { RelatedEventChip } from "@/lib/types/messaging";

export function RelatedEventMiniCard({
  event,
}: {
  event: RelatedEventChip;
}) {
  return (
    <Link
      href={event.path}
      className="mx-4 mt-3 flex items-center gap-3 rounded-[var(--radius-md)] border border-border bg-surface-muted/50 p-2.5 transition-colors hover:border-border-strong dark:bg-surface-elevated/50"
    >
      {event.banner_url ? (
        <span className="relative h-12 w-16 shrink-0 overflow-hidden rounded-[var(--radius-sm)] border border-border bg-ink">
          <Media src={event.banner_url} alt="" className="h-full w-full" />
        </span>
      ) : (
        <span
          className="flex h-12 w-16 shrink-0 items-center justify-center rounded-[var(--radius-sm)] border border-border bg-ink text-[10px] font-bold uppercase tracking-wide text-primary"
          aria-hidden
        >
          Event
        </span>
      )}
      <span className="min-w-0">
        <span className="block text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Related event
        </span>
        <span className="mt-0.5 block truncate text-sm font-extrabold text-foreground">
          {event.title}
        </span>
      </span>
    </Link>
  );
}
