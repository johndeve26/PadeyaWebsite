"use client";

import { Button } from "@/components/ui";
import { track } from "@/lib/analytics";
import { TrackedAction } from "@/lib/analytics-taxonomy";
import { EXTERNAL_GALLERY_LABELS } from "@/lib/types/memories";

export function ExternalGalleryLink({
  url,
  label,
  eventId,
  eventTitle,
}: {
  url: string;
  label: string | null | undefined;
  eventId: string;
  eventTitle: string;
}) {
  const found = EXTERNAL_GALLERY_LABELS.find((x) => x.value === label);
  const display = found?.label ?? "View more photos";
  return (
    <section className="rounded-2xl border border-border bg-card p-5">
      <h2 className="text-lg font-extrabold tracking-tight">
        More from {eventTitle}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">{display}</p>
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-4 inline-flex"
        onClick={() =>
          track(TrackedAction.EXTERNAL_GALLERY_CLICKED, {
            targetEventId: eventId,
          })
        }
      >
        <Button type="button" variant="secondary">
          View more photos →
        </Button>
      </a>
    </section>
  );
}
