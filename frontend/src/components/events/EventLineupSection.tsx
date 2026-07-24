import { Media } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import type { EventPerson } from "@/lib/types/events";

import { EventDetailPanel } from "./EventDetailPanel";

export function EventLineupSection({ people }: { people: EventPerson[] }) {
  const rows = [...people]
    .filter((person) => person.name?.trim())
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  if (!rows.length) return null;

  return (
    <EventDetailPanel title="Performers & speakers">
      <div className="grid gap-3 sm:grid-cols-2">
        {rows.map((person, index) => (
          <article
            key={person.id ?? `person-${index}`}
            className="flex gap-3 rounded-[var(--radius-md)] border border-border bg-muted/40 p-3.5"
          >
            {person.image_url ? (
              <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-full bg-surface-dark">
                <Media src={person.image_url} alt="" className="object-cover" />
              </div>
            ) : (
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-ink text-sm font-extrabold text-accent">
                {person.name.slice(0, 1).toUpperCase()}
              </div>
            )}
            <div className="min-w-0 space-y-1">
              <p className="font-extrabold text-foreground">{person.name}</p>
              {person.role ? (
                <p className="text-sm text-muted-foreground">{person.role}</p>
              ) : null}
              {person.performance_time ? (
                <p className="text-xs font-semibold text-foreground">
                  On at {formatDateTime(person.performance_time)}
                </p>
              ) : null}
              {person.bio ? (
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {person.bio}
                </p>
              ) : null}
              {person.social_url ? (
                <a
                  href={person.social_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block text-xs font-bold uppercase tracking-wide text-foreground underline decoration-accent underline-offset-2"
                >
                  Social
                </a>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </EventDetailPanel>
  );
}
