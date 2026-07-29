"use client";

import Link from "next/link";

import { Badge, Button, SectionHeader } from "@/components/ui";
import { formatDate } from "@/lib/format";
import type { PassportEventSafe } from "@/lib/types/passport";

type Props = {
  events: PassportEventSafe[];
};

export function VerifiedNightsOut({ events }: Props) {
  if (events.length === 0) {
    return (
      <section className="space-y-3">
        <SectionHeader
          eyebrow="Nights out"
          title="Verified nights out"
          description="Checked-in events only. Private and hidden locations stay off this page."
        />
        <p className="text-sm text-muted-foreground">
          Public checked-in events will appear here when this fan chooses to
          show them.
        </p>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <SectionHeader
        eyebrow="Nights out"
        title="Verified nights out"
        description="Checked-in events only. Private and hidden locations stay off this page."
      />
      <ul className="space-y-3">
        {events.map((ev, index) => (
          <li
            key={ev.event_id}
            className="relative rounded-[var(--radius-lg)] border border-border bg-card p-4 shadow-[var(--shadow-soft)] sm:p-5"
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
                    Night {index + 1}
                  </span>
                  <Badge tone="success" size="sm">
                    Checked in
                  </Badge>
                </div>
                <h3 className="text-lg font-extrabold tracking-tight text-foreground">
                  <Link
                    href={`/events/${ev.slug}`}
                    className="underline-offset-2 hover:underline"
                  >
                    {ev.title}
                  </Link>
                </h3>
                <p className="text-sm text-muted-foreground">
                  {formatDate(ev.start_datetime)}
                  {ev.host_display_name ? ` · ${ev.host_display_name}` : ""}
                  {ev.city ? ` · ${ev.city}` : ""}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {ev.host_username ? (
                  <Link href={`/@${ev.host_username}`}>
                    <Button size="sm" variant="primary">
                      Host Legacy
                    </Button>
                  </Link>
                ) : null}
                <Link href={`/events/${ev.slug}`}>
                  <Button size="sm" variant="ghost">
                    View event
                  </Button>
                </Link>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
