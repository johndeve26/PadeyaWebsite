"use client";

import { Input, Textarea } from "@/components/ui";
import type { EventCategory } from "@/lib/types/events";

import { EventStudioSection } from "../EventStudioSection";
import {
  StudioDescriptionAI,
  StudioTitleAI,
} from "../StudioAIAssist";
import { TaxonomyFields } from "../TaxonomyFields";
import type { EventStudioValues } from "../types";

export function BasicsStep({
  values,
  categories,
  mode,
  eventId,
  onChange,
  onApplyHostDefaults,
}: {
  values: EventStudioValues;
  categories: EventCategory[];
  mode: "create" | "edit";
  eventId?: string | null;
  onChange: <K extends keyof EventStudioValues>(
    key: K,
    value: EventStudioValues[K],
  ) => void;
  onApplyHostDefaults?: () => void;
}) {
  const categoryName =
    categories.find((c) => c.id === values.category_id)?.name ?? null;

  return (
    <EventStudioSection
      title="Basics"
      description="What guests see first on Pàdéyá — the name of the night, a short pitch, and how people discover it."
    >
      <div className="space-y-2">
        <Input
          label="Title"
          required
          hint="The main name on the event page and in search. Keep it clear (e.g. “Afrobeats Rooftop Night”)."
          value={values.title}
          onChange={(e) => onChange("title", e.target.value)}
        />
        <StudioTitleAI
          values={values}
          categoryName={categoryName}
          eventId={eventId}
          onApplyTitle={(title) => onChange("title", title)}
        />
      </div>
      <Input
        label="Slug"
        hint={
          mode === "create"
            ? "This becomes the public URL (/events/your-slug). We create it from your title when you first save — you can change it later."
            : "The public URL ending for this event. Only change it if buyers are not already sharing the old link."
        }
        value={values.slug}
        onChange={(e) => onChange("slug", e.target.value)}
        disabled={mode === "create"}
      />
      <Input
        label="Short tagline"
        hint="One punchy line under the title — what makes this night special in under ~80 characters."
        value={values.short_tagline}
        onChange={(e) => onChange("short_tagline", e.target.value)}
        placeholder="One sharp line that sells the night"
      />
      <div className="space-y-2">
        <Textarea
          label="Description"
          required
          minLength={10}
          rows={6}
          hint="Tell first-time guests what the event is, who it is for, and why they should come. At least 10 characters to save."
          value={values.description}
          onChange={(e) => onChange("description", e.target.value)}
        />
        <StudioDescriptionAI
          values={values}
          categoryName={categoryName}
          eventId={eventId}
          onApplyDescription={(description) =>
            onChange("description", description)
          }
        />
      </div>
      <TaxonomyFields
        values={values}
        categories={categories}
        onChange={(key, value) => onChange(key, value)}
        onApplyHostDefaults={onApplyHostDefaults}
      />
    </EventStudioSection>
  );
}
