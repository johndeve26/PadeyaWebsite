import { formatDateTime } from "@/lib/format";
import type { EventAgendaItem } from "@/lib/types/events";

import { EventDetailPanel } from "./EventDetailPanel";

function agendaTimeLabel(item: EventAgendaItem): string | null {
  if (!item.start_time && !item.end_time) return null;
  const start = item.start_time ? formatDateTime(item.start_time) : null;
  const end = item.end_time ? formatDateTime(item.end_time) : null;
  if (start && end) return `${start} – ${end}`;
  return start || end;
}

export function EventAgendaSection({ items }: { items: EventAgendaItem[] }) {
  const rows = [...items]
    .filter((item) => item.title?.trim())
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  if (!rows.length) return null;

  return (
    <EventDetailPanel title="Agenda">
      <ol className="space-y-0">
        {rows.map((item, index) => {
          const when = agendaTimeLabel(item);
          return (
            <li
              key={item.id ?? `agenda-${index}`}
              className="relative flex gap-4 border-b border-border py-4 last:border-0 last:pb-0 first:pt-0"
            >
              <div className="flex w-8 shrink-0 flex-col items-center pt-0.5">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-ink text-[11px] font-extrabold text-accent">
                  {index + 1}
                </span>
                {index < rows.length - 1 ? (
                  <span
                    aria-hidden
                    className="mt-2 w-px flex-1 min-h-[1.25rem] bg-border"
                  />
                ) : null}
              </div>
              <div className="min-w-0 flex-1 pb-1">
                <p className="font-extrabold text-foreground">{item.title}</p>
                <p className="mt-0.5 text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                  {item.type.replaceAll("_", " ")}
                  {when ? ` · ${when}` : null}
                </p>
                {item.description ? (
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                    {item.description}
                  </p>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
    </EventDetailPanel>
  );
}
