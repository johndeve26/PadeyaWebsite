"use client";

import { EventStudioSection } from "../EventStudioSection";
import { MediaPreviewUploader } from "../MediaPreviewUploader";
import type { EventStudioValues } from "../types";

export function MediaStep({
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
      title="Media & Branding"
      description="Banners, crops, gallery, teasers, and sponsors — upload what you own."
    >
      <MediaPreviewUploader
        values={values}
        eventId={eventId}
        media={values.media_items}
        onChange={(key, value) =>
          onChange(key as keyof EventStudioValues, value as never)
        }
      />
    </EventStudioSection>
  );
}
