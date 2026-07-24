"use client";

import Link from "next/link";

import { SectionLabel } from "@/components/personal/command-center/SectionLabel";
import { Button, Card } from "@/components/ui";

/**
 * New-user empty home — friendly welcome + primary CTAs.
 * Compact card — keep it simple. Become a host stays secondary.
 */
export function WelcomeEmptySection({
  showBecomeHost,
}: {
  showBecomeHost: boolean;
}) {
  return (
    <section className="min-w-0 space-y-3">
      <SectionLabel>Welcome</SectionLabel>
      <Card className="min-w-0 space-y-4">
        <div className="min-w-0 space-y-1.5">
          <h2 className="text-lg font-bold tracking-tight text-foreground">
            Welcome to your Personal Command Center
          </h2>
          <p className="max-w-xl text-sm leading-relaxed text-muted-foreground">
            Find your next night out on Pàdéyá, set up your Fan Passport, or
            promote an event you love. Your tickets and pickups will show up
            here.
          </p>
        </div>
        <div className="flex min-w-0 flex-wrap gap-2">
          <Link href="/events">
            <Button size="sm">Browse events</Button>
          </Link>
          <Link href="/dashboard/passport">
            <Button size="sm" variant="secondary">
              Set up Passport
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
      </Card>
    </section>
  );
}
