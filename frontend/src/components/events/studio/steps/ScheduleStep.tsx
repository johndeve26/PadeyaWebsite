"use client";

import { Input, Select } from "@/components/ui";

import { AgendaBuilder, agendaEndAfterStartError } from "../AgendaBuilder";
import { EventStudioSection } from "../EventStudioSection";
import type { EventStudioValues } from "../types";

const TIMEZONE_OPTIONS = [
  "Africa/Lagos",
  "Africa/Accra",
  "Africa/Nairobi",
  "Africa/Johannesburg",
  "UTC",
  "Europe/London",
  "America/New_York",
] as const;

export function ScheduleStep({
  values,
  onChange,
}: {
  values: EventStudioValues;
  onChange: <K extends keyof EventStudioValues>(
    key: K,
    value: EventStudioValues[K],
  ) => void;
}) {
  const endError = agendaEndAfterStartError(
    values.start_datetime,
    values.end_datetime,
  );
  const doorsError =
    values.doors_open_datetime && values.start_datetime
      ? (() => {
          const doors = new Date(values.doors_open_datetime).getTime();
          const start = new Date(values.start_datetime).getTime();
          if (Number.isNaN(doors) || Number.isNaN(start)) return null;
          if (doors > start) {
            return "Doors usually open at or before the official start time.";
          }
          return null;
        })()
      : null;

  const timezoneKnown = TIMEZONE_OPTIONS.includes(
    values.timezone as (typeof TIMEZONE_OPTIONS)[number],
  );

  return (
    <EventStudioSection
      title="Schedule & Agenda"
      description="Set when the night starts and ends, when doors open, timezone, and an optional run-of-show guests can follow."
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Starts"
          type="datetime-local"
          required
          hint="Official start time shown on the event page."
          value={values.start_datetime}
          onChange={(e) => onChange("start_datetime", e.target.value)}
        />
        <Input
          label="Ends"
          type="datetime-local"
          required
          hint="When you expect the event to finish."
          error={endError ?? undefined}
          value={values.end_datetime}
          onChange={(e) => onChange("end_datetime", e.target.value)}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Doors open"
          type="datetime-local"
          hint="Optional. When guests may arrive and enter."
          error={doorsError ?? undefined}
          value={values.doors_open_datetime}
          onChange={(e) => onChange("doors_open_datetime", e.target.value)}
        />
        <Select
          label="Timezone"
          hint="Event times are shown in this zone (IANA name)."
          value={values.timezone}
          onChange={(e) => onChange("timezone", e.target.value)}
        >
          {!timezoneKnown && values.timezone ? (
            <option value={values.timezone}>{values.timezone}</option>
          ) : null}
          {TIMEZONE_OPTIONS.map((zone) => (
            <option key={zone} value={zone}>
              {zone}
            </option>
          ))}
        </Select>
      </div>
      <AgendaBuilder
        items={values.agenda_items}
        onChange={(items) => onChange("agenda_items", items)}
      />
    </EventStudioSection>
  );
}
