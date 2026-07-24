"use client";

import Link from "next/link";

import { SectionLabel } from "@/components/personal/command-center/SectionLabel";
import { Button, Card } from "@/components/ui";
import { shouldShowCommunityStrip } from "@/lib/personal-command-center";

/**
 * Messages / Connect / Following — hide when empty.
 * Counts only for the signed-in user (no private Connect payloads).
 */
export function CommunitySection({
  unreadMessages,
  connectPending,
  followingCount,
}: {
  unreadMessages: number | null;
  connectPending: number | null;
  followingCount: number | null;
}) {
  if (
    !shouldShowCommunityStrip({
      unreadMessages,
      connectPending,
      followingCount,
    })
  ) {
    return null;
  }

  const unread = unreadMessages ?? 0;
  const pending = connectPending ?? 0;
  const following = followingCount ?? 0;
  const showConnect = connectPending != null && pending > 0;
  const showFollowing = followingCount != null && following > 0;

  return (
    <section className="min-w-0 space-y-3">
      <SectionLabel>Messages and community</SectionLabel>
      <Card className="min-w-0 space-y-3">
        {unread > 0 ? (
          <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="font-semibold text-foreground">
                {unread} unread message{unread === 1 ? "" : "s"}
              </p>
              <p className="text-sm text-muted-foreground">
                Fan ↔ host inbox and Fan Connect threads.
              </p>
            </div>
            <Link href="/dashboard/messages" className="shrink-0">
              <Button size="sm">Open Messages</Button>
            </Link>
          </div>
        ) : null}

        {showConnect ? (
          <div
            className={
              unread > 0
                ? "flex min-w-0 flex-wrap items-center justify-between gap-3 border-t border-border pt-3"
                : "flex min-w-0 flex-wrap items-center justify-between gap-3"
            }
          >
            <p className="min-w-0 text-sm text-foreground">
              {pending} Connect request{pending === 1 ? "" : "s"} pending
            </p>
            <Link href="/connect/requests" className="shrink-0">
              <Button size="sm" variant="secondary">
                Review
              </Button>
            </Link>
          </div>
        ) : null}

        {showFollowing ? (
          <div
            className={
              unread > 0 || showConnect
                ? "flex min-w-0 flex-wrap items-center justify-between gap-3 border-t border-border pt-3"
                : "flex min-w-0 flex-wrap items-center justify-between gap-3"
            }
          >
            <p className="min-w-0 text-sm text-muted-foreground">
              Following {following} host{following === 1 ? "" : "s"}
            </p>
            <Link href="/dashboard/following" className="shrink-0">
              <Button size="sm" variant="ghost">
                Following
              </Button>
            </Link>
          </div>
        ) : null}
      </Card>
    </section>
  );
}
