import { Badge } from "@/components/ui";
import type { EventStatus } from "@/lib/types/events";

const labels: Record<EventStatus, string> = {
  draft: "Draft",
  pending_review: "Pending review",
  published: "Published",
  paused: "Paused",
  completed: "Completed",
  cancelled: "Cancelled",
  rejected: "Rejected",
  archived: "Archived",
};

export function StatusBadge({ status }: { status: EventStatus | string }) {
  const tone =
    status === "published"
      ? "accent"
      : status === "rejected" || status === "cancelled"
        ? "dark"
        : "neutral";
  return <Badge tone={tone}>{labels[status as EventStatus] ?? status}</Badge>;
}
