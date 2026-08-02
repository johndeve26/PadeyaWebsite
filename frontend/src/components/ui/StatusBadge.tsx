import { Badge, type BadgeProps } from "./Badge";

const toneMap: Record<string, BadgeProps["tone"]> = {
  published: "accent",
  active: "accent",
  approved: "accent",
  approve: "accent",
  successful: "accent",
  issued: "accent",
  paid: "success",
  completed: "info",
  verified: "success",
  accepted: "success",
  checked_in: "success",
  pending: "warning",
  under_review: "warning",
  requested: "warning",
  processing: "warning",
  reviewing: "warning",
  flagged: "warning",
  flag: "warning",
  transferred: "outline",
  draft: "neutral",
  paused: "neutral",
  disabled: "neutral",
  inactive: "neutral",
  archived: "neutral",
  expired: "neutral",
  scheduled: "warning",
  hidden_by_admin: "danger",
  credit: "accent",
  debit: "neutral",
  declined: "danger",
  rejected: "danger",
  cancelled: "danger",
  failed: "danger",
  removed: "danger",
  remove: "danger",
  refunded: "outline",
  escalated: "warning",
  suspended: "danger",
  banned: "danger",
  deleted: "danger",
  restricted: "warning",
  locked: "danger",
  high: "danger",
  medium: "warning",
  low: "success",
  awaiting_pickup: "success",
  collect_at_stand: "warning",
  fulfilled: "success",
  confirmed: "success",
  ready_for_pickup: "warning",
  picked_up: "success",
  pending_payment: "warning",
};

export function StatusBadge({
  status,
  label,
}: {
  status: string;
  label?: string;
}) {
  const key = status.toLowerCase();
  const text = label ?? status.replace(/_/g, " ");
  return (
    <Badge tone={toneMap[key] ?? "neutral"} title={text}>
      {text}
    </Badge>
  );
}
