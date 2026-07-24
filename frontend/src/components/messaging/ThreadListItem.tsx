import Link from "next/link";

import { ParticipantAvatar } from "@/components/messaging/ParticipantAvatar";
import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatRelativeShort } from "@/lib/format-relative";
import type { ThreadListItem as Thread } from "@/lib/types/messaging";

function statusBadges(thread: Thread) {
  const badges: { key: string; label: string; tone: "accent" | "warning" | "danger" | "neutral" | "outline" }[] =
    [];
  if (thread.thread_type === "fan_fan" || thread.connect_context) {
    badges.push({
      key: "fan-connect",
      label: thread.connect_context?.badge || "Fan Connect",
      tone: "accent",
    });
  }
  // Thread-level unread flag (not a per-message count — receipts are cursor-based).
  if (thread.unread) {
    badges.push({ key: "unread", label: "Unread", tone: "accent" });
  }
  if (thread.is_request || thread.status === "request") {
    badges.push({ key: "request", label: "Request", tone: "warning" });
  }
  if (thread.archived || thread.status === "archived") {
    badges.push({ key: "archived", label: "Archived", tone: "neutral" });
  }
  if (thread.status === "reported") {
    badges.push({ key: "reported", label: "Reported", tone: "danger" });
  }
  if (thread.status === "blocked" || thread.blocked) {
    badges.push({ key: "blocked", label: "Blocked", tone: "danger" });
  }
  if (thread.related_event) {
    badges.push({
      key: "event",
      label: thread.related_event.title,
      tone: "outline",
    });
  }
  return badges;
}

export function ThreadListItem({
  thread,
  href,
  active,
}: {
  thread: Thread;
  href: string;
  active?: boolean;
}) {
  const badges = statusBadges(thread);
  const stamp = formatRelativeShort(thread.last_message_at || thread.created_at);

  return (
    <Link
      href={href}
      className={cn(
        "block rounded-[var(--radius-md)] border px-3 py-3 transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
        active
          ? "border-primary/40 bg-primary/10"
          : "border-transparent hover:bg-surface-muted dark:hover:bg-surface-elevated",
        thread.unread ? "bg-surface-muted/80 dark:bg-surface-elevated/80" : "",
      )}
    >
      <div className="flex items-start gap-3">
        <div className="relative shrink-0">
          <ParticipantAvatar
            name={thread.counterpart.display_name}
            avatarUrl={thread.counterpart.avatar_url}
          />
          {thread.unread ? (
            <span
              className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-card bg-primary dark:border-surface"
              aria-label="Unread"
            />
          ) : null}
        </div>
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center justify-between gap-2">
            <p
              className={cn(
                "truncate font-extrabold",
                thread.unread ? "text-heading" : "text-foreground",
              )}
            >
              {thread.counterpart.display_name}
            </p>
            {stamp ? (
              <span
                className={cn(
                  "shrink-0 text-[10px] font-semibold",
                  thread.unread
                    ? "text-foreground"
                    : "text-muted-foreground",
                )}
              >
                {stamp}
              </span>
            ) : null}
          </div>
          {thread.connect_context?.context_label ? (
            <p className="line-clamp-1 text-xs font-medium text-primary/90">
              {thread.connect_context.context_label}
            </p>
          ) : null}
          <p
            className={cn(
              "line-clamp-1 text-sm",
              thread.unread
                ? "font-semibold text-foreground"
                : "text-muted-foreground",
            )}
          >
            {thread.last_message_preview || "No messages yet"}
          </p>
          {badges.length ? (
            <div className="flex flex-wrap gap-1.5">
              {badges.map((b) => (
                <Badge key={b.key} tone={b.tone} size="sm">
                  {b.label}
                </Badge>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </Link>
  );
}
