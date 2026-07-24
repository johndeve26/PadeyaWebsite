import type { EventItem } from "@/lib/types/events";

import { EventDetailPanel, EventInfoTile } from "./EventDetailPanel";

function InfoBlock({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <EventInfoTile label={label}>
      <p className="whitespace-pre-wrap">{value}</p>
    </EventInfoTile>
  );
}

/** What to expect, dress code, bring list, and prohibited items. */
export function EventGuestPrepSection({ event }: { event: EventItem }) {
  const has =
    event.what_to_expect ||
    event.what_to_bring ||
    event.dress_code ||
    event.prohibited_items;
  if (!has) return null;

  return (
    <EventDetailPanel title="What to expect">
      <div className="grid gap-3 sm:grid-cols-2 sm:gap-4">
        {event.what_to_expect ? (
          <InfoBlock label="What to expect" value={event.what_to_expect} />
        ) : null}
        {event.dress_code ? (
          <InfoBlock label="Dress code" value={event.dress_code} />
        ) : null}
        {event.what_to_bring ? (
          <InfoBlock label="What to bring" value={event.what_to_bring} />
        ) : null}
        {event.prohibited_items ? (
          <InfoBlock label="Prohibited" value={event.prohibited_items} />
        ) : null}
      </div>
    </EventDetailPanel>
  );
}

/** Accessibility and parking — venue logistics guests need before arriving. */
export function EventAccessLogisticsSection({ event }: { event: EventItem }) {
  if (!event.accessibility_notes && !event.parking_info) return null;

  return (
    <EventDetailPanel title="Accessibility & parking">
      <div className="grid gap-3 sm:grid-cols-2 sm:gap-4">
        {event.accessibility_notes ? (
          <InfoBlock
            label="Accessibility"
            value={event.accessibility_notes}
          />
        ) : null}
        {event.parking_info ? (
          <InfoBlock label="Parking" value={event.parking_info} />
        ) : null}
      </div>
    </EventDetailPanel>
  );
}
