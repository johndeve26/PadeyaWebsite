"use client";

import { MapPreviewCard } from "@/components/events/MapPreviewCard";
import { Button } from "@/components/ui";
import { fanMapPreview, studioMapsOpenUrl } from "@/lib/location-studio-preview";

import { StudioFieldGroup } from "./studio-ui";
import type { EventStudioValues } from "./types";

export function LocationPublicPreview({
  values,
}: {
  values: EventStudioValues;
}) {
  const preview = fanMapPreview(values);
  const openUrl = studioMapsOpenUrl(values);

  return (
    <StudioFieldGroup title={preview.headline}>
      <div className="space-y-3 rounded-[var(--radius-lg)] border border-border bg-card/60 p-4 dark:bg-surface-elevated/60">
        {preview.lines.map((line) => (
          <p key={line} className="text-sm font-semibold text-foreground">
            {line}
          </p>
        ))}
        {preview.note ? (
          <p className="text-xs leading-relaxed text-muted-foreground">{preview.note}</p>
        ) : null}
      </div>

      {preview.mode === "exact" &&
      preview.mapLatitude &&
      preview.mapLongitude ? (
        <MapPreviewCard
          latitude={preview.mapLatitude}
          longitude={preview.mapLongitude}
          mode="exact"
          label={preview.mapLabel}
          openUrl={openUrl}
        />
      ) : null}

      {preview.mode === "approximate" &&
      preview.mapLatitude &&
      preview.mapLongitude ? (
        <MapPreviewCard
          latitude={preview.mapLatitude}
          longitude={preview.mapLongitude}
          mode="approximate"
          label={preview.mapLabel}
          openUrl={openUrl}
        />
      ) : null}

      {preview.mode === "hidden" ? (
        <p className="text-xs text-muted-foreground">
          Public map uses the approximate area pin only — exact street stays private.
        </p>
      ) : null}

      {preview.mode === "none" ? null : (
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant="secondary"
            disabled={!openUrl}
            onClick={() => {
              if (openUrl) {
                window.open(openUrl, "_blank", "noopener,noreferrer");
              }
            }}
          >
            Open map preview
          </Button>
          <p className="text-xs text-muted-foreground">
            Opens Google Maps in a new tab — same pin fans get on the event page.
          </p>
        </div>
      )}
    </StudioFieldGroup>
  );
}
