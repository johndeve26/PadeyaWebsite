"use client";

import { AttendeeQuestionBuilder } from "../AttendeeQuestionBuilder";
import { EventStudioSection } from "../EventStudioSection";
import type { EventStudioValues } from "../types";

export function QuestionsStep({
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
      title="Attendee Questions"
      description="Optional questions collected at checkout (size, meal preference, company, etc.)."
    >
      <AttendeeQuestionBuilder
        questions={values.checkout_questions}
        onChange={(questions) => onChange("checkout_questions", questions)}
      />
    </EventStudioSection>
  );
}
