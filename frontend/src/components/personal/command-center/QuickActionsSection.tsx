"use client";

import Link from "next/link";

import { SectionLabel } from "@/components/personal/command-center/SectionLabel";
import { Button } from "@/components/ui";

/** Short action row — not a feature-dump grid. */
export function QuickActionsSection({
  showBecomeHost,
}: {
  showBecomeHost: boolean;
}) {
  return (
    <section className="min-w-0 space-y-3">
      <SectionLabel>Quick actions</SectionLabel>
      <div className="flex min-w-0 flex-wrap gap-2">
        <Link href="/events">
          <Button size="sm">Browse events</Button>
        </Link>
        <Link href="/dashboard/tickets">
          <Button size="sm" variant="secondary">
            View tickets
          </Button>
        </Link>
        <Link href="/dashboard/messages">
          <Button size="sm" variant="secondary">
            Open messages
          </Button>
        </Link>
        <Link href="/dashboard/passport">
          <Button size="sm" variant="secondary">
            Open Passport
          </Button>
        </Link>
        <Link href="/ambassadors/events">
          <Button size="sm" variant="secondary">
            Promote an event
          </Button>
        </Link>
        {showBecomeHost ? (
          <Link href="/host/onboarding">
            <Button size="sm" variant="ghost">
              Become a host
            </Button>
          </Link>
        ) : null}
      </div>
      {!showBecomeHost ? (
        <p className="text-xs text-muted-foreground">
          Switch to a Host workspace from the sidebar switcher.
        </p>
      ) : null}
    </section>
  );
}
