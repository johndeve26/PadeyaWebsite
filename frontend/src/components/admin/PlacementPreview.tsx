"use client";

import { PadeyaPicksSection } from "@/components/discovery/PadeyaPicksSection";
import { Card } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { EventItem } from "@/lib/types/events";

/**
 * Admin live preview of a featured placement set as public Pàdéyá Picks.
 */
export function PlacementPreview({
  events,
  title,
  description,
  eyebrow,
  emptyMessage = "Assign at least one event to preview the placement.",
  className = "",
}: {
  events: EventItem[];
  title?: string;
  description?: string;
  eyebrow?: string;
  emptyMessage?: string;
  className?: string;
}) {
  return (
    <Card className={cn("overflow-hidden p-0", className)}>
      <div className="border-b border-border px-5 py-4">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Preview
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          Public Pàdéyá Picks layout for this assignment.
        </p>
      </div>
      {events.length ? (
        <PadeyaPicksSection
          events={events}
          title={title}
          description={description}
          eyebrow={eyebrow}
          layout="spotlight"
          showSlotLabels
          className="border-b-0 py-8"
        />
      ) : (
        <div className="px-5 py-10 text-sm text-muted-foreground">{emptyMessage}</div>
      )}
    </Card>
  );
}
