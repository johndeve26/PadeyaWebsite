"use client";

import { Input, Textarea } from "@/components/ui";

import { EventStudioSection } from "../EventStudioSection";
import { PolicySelector } from "../PolicySelector";
import type { EventStudioValues } from "../types";

export function PoliciesStep({
  values,
  onChange,
}: {
  values: EventStudioValues;
  onChange: <K extends keyof EventStudioValues>(
    key: K,
    value: EventStudioValues[K],
  ) => void;
}) {
  return (
    <EventStudioSection
      title="Policies & Safety"
      description="Structured guest rules: refunds, cancellation, age/ID, dress code, entry logistics, safety, door sales, re-entry, and check-in window."
    >
      <PolicySelector
        values={values}
        onChange={(key, value) =>
          onChange(key as keyof EventStudioValues, value as never)
        }
      />
      <Textarea
        label="What to expect"
        rows={3}
        hint="Describe the flow of the night in plain language."
        value={values.what_to_expect}
        onChange={(e) => onChange("what_to_expect", e.target.value)}
      />
      <Textarea
        label="What to bring"
        rows={2}
        hint="Practical checklist: ID, ticket QR, cash/card, jacket, etc."
        value={values.what_to_bring}
        onChange={(e) => onChange("what_to_bring", e.target.value)}
      />
      <Textarea
        label="Prohibited items"
        rows={2}
        hint="What security will not allow."
        value={values.prohibited_items}
        onChange={(e) => onChange("prohibited_items", e.target.value)}
      />
      <Input
        label="Dress code"
        hint="What guests should wear."
        value={values.dress_code}
        onChange={(e) => onChange("dress_code", e.target.value)}
      />
      <Textarea
        label="Entry requirements"
        rows={2}
        hint="Door rules beyond the ticket."
        value={values.entry_requirements}
        onChange={(e) => onChange("entry_requirements", e.target.value)}
      />
      <Textarea
        label="Accessibility notes"
        rows={2}
        hint="Elevators, wheelchair access, quiet areas, contact for access needs."
        value={values.accessibility_notes}
        onChange={(e) => onChange("accessibility_notes", e.target.value)}
      />
      <Textarea
        label="Parking info"
        rows={2}
        hint="Where to park, valet, or rideshare guidance."
        value={values.parking_info}
        onChange={(e) => onChange("parking_info", e.target.value)}
      />
    </EventStudioSection>
  );
}
