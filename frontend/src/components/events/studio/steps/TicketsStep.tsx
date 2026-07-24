"use client";

import { Input } from "@/components/ui";
import {
  deactivateTicketType,
  deleteTicketType,
} from "@/lib/events-api";

import { AccessRulesFields } from "../AccessRulesFields";
import { EventStudioSection } from "../EventStudioSection";
import { TicketTypeBuilder } from "../TicketTypeBuilder";
import type { EventStudioValues } from "../types";

export function TicketsStep({
  values,
  eventId,
  onChange,
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
      title="Tickets & Access"
      description="Configure ticket tiers guests can buy, then set how discoverable the event is. Sold tiers cannot be hard-deleted — deactivate them instead so orders stay intact."
    >
      <TicketTypeBuilder
        drafts={values.ticket_drafts}
        onChange={(drafts) => onChange("ticket_drafts", drafts)}
        eventId={eventId}
        onDeactivate={
          eventId
            ? async (ticketTypeId) => {
                await deactivateTicketType(eventId, ticketTypeId);
              }
            : undefined
        }
        onDeleteUnused={
          eventId
            ? async (ticketTypeId) => {
                await deleteTicketType(eventId, ticketTypeId);
              }
            : undefined
        }
      />
      <Input
        label="Capacity"
        type="number"
        min={1}
        hint="Optional overall venue cap. Leave blank to limit stock per ticket tier only."
        value={values.capacity}
        onChange={(e) => onChange("capacity", e.target.value)}
      />
      <AccessRulesFields
        values={values}
        onChange={(key, value) => onChange(key, value)}
      />
    </EventStudioSection>
  );
}
