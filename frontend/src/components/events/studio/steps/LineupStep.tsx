"use client";

import { EventStudioSection } from "../EventStudioSection";
import { PeopleLineupBuilder } from "../PeopleLineupBuilder";
import type { EventStudioValues } from "../types";

export function LineupStep({
  values,
  onChange,
  eventId,
}: {
  values: EventStudioValues;
  eventId?: string;
  onChange: <K extends keyof EventStudioValues>(
    key: K,
    value: EventStudioValues[K],
  ) => void;
}) {
  return (
    <EventStudioSection
      title="Guests / Performers / Speakers"
      description="Manage the people on the bill — artists, DJs, speakers, comedians, ministers, hosts, and panelists. Add, edit, remove, and reorder."
    >
      <PeopleLineupBuilder
        people={values.people}
        eventId={eventId}
        onChange={(people) => onChange("people", people)}
      />
    </EventStudioSection>
  );
}
