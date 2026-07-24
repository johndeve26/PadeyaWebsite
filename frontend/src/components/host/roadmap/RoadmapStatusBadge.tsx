import { Badge } from "@/components/ui";
import type { RoadmapStatus } from "@/lib/host-roadmap";
import { roadmapStatusLabel } from "@/lib/host-roadmap";

const toneByStatus: Record<
  RoadmapStatus,
  "accent" | "neutral" | "dark" | "warning"
> = {
  done: "accent",
  in_progress: "warning",
  not_started: "neutral",
  skipped: "dark",
};

export function RoadmapStatusBadge({ status }: { status: RoadmapStatus }) {
  return (
    <Badge tone={toneByStatus[status]}>{roadmapStatusLabel(status)}</Badge>
  );
}
