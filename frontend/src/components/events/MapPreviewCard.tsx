"use client";

import { cn } from "@/lib/cn";
import { mapEmbedSrc } from "@/lib/event-maps";

export function MapPreviewCard({
  latitude,
  longitude,
  mode,
  label,
  openUrl,
  className,
}: {
  latitude: string;
  longitude: string;
  mode: "exact" | "approximate";
  label?: string | null;
  openUrl?: string | null;
  className?: string;
}) {
  const zoom = mode === "exact" ? 15 : 12;
  return (
    <div
      className={cn(
        "overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)]",
        "dark:border-border-strong/40 dark:bg-surface-elevated dark:shadow-[var(--shadow)]",
        className,
      )}
    >
      <div className="relative bg-surface-inset">
        {/* Loading / letterbox fill behind the embed */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,var(--surface-muted)_0%,var(--surface-inset)_50%,var(--surface)_100%)]"
        />
        <iframe
          title={mode === "exact" ? "Exact venue map" : "Approximate area map"}
          className="relative aspect-[16/10] w-full bg-surface-inset sm:aspect-[2/1]"
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
          src={mapEmbedSrc(latitude, longitude, zoom)}
        />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink via-ink/75 to-transparent px-4 pb-3.5 pt-14">
          <p className="text-xs font-extrabold uppercase tracking-[0.12em] text-primary">
            {mode === "exact" ? "Exact location" : "Approximate area shown"}
          </p>
          {label ? (
            <p className="mt-0.5 text-sm font-semibold text-paper drop-shadow-sm">
              {label}
            </p>
          ) : null}
        </div>
      </div>
      {openUrl ? (
        <div className="flex items-center justify-between gap-3 border-t border-border bg-surface-muted/40 px-4 py-3 dark:bg-surface-inset/80">
          <p className="text-xs leading-relaxed text-body">
            {mode === "exact"
              ? "Open the pin in Google Maps for directions."
              : "Area search only — exact street stays private."}
          </p>
          <a
            href={openUrl}
            target="_blank"
            rel="noreferrer"
            className="shrink-0 text-xs font-extrabold uppercase tracking-wide text-heading underline decoration-primary underline-offset-4"
          >
            Open in Google Maps
          </a>
        </div>
      ) : null}
    </div>
  );
}
