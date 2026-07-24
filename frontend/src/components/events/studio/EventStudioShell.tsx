"use client";

import type { ReactNode } from "react";

import { PageHeader } from "@/components/ui";

import { EventStudioStepper } from "./EventStudioStepper";
import { UnsavedChangesBar } from "./UnsavedChangesBar";
import {
  studioStepCompletion,
  STUDIO_STEPS,
  type EventStudioValues,
  type StudioStepId,
} from "./types";

export function EventStudioShell({
  title,
  description,
  currentStep,
  onStepChange,
  values,
  children,
  actions,
  lastSavedAt,
  dirty = false,
  saving = false,
  onSaveDraft,
  footer,
  mobileBar,
}: {
  title: string;
  description?: string;
  currentStep: StudioStepId;
  onStepChange: (id: StudioStepId) => void;
  values: EventStudioValues;
  children: ReactNode;
  actions?: ReactNode;
  lastSavedAt?: string | null;
  dirty?: boolean;
  saving?: boolean;
  onSaveDraft?: () => void;
  footer?: ReactNode;
  mobileBar?: ReactNode;
}) {
  const completed = studioStepCompletion(values);
  const stepIndex = STUDIO_STEPS.findIndex((s) => s.id === currentStep);
  const stepMeta = STUDIO_STEPS[stepIndex];

  return (
    <div className="relative space-y-6 pb-28 lg:pb-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 -top-6 h-56 bg-[radial-gradient(ellipse_at_top,color-mix(in_srgb,var(--brand-green)_14%,transparent),transparent_65%)]"
      />

      <div className="relative space-y-5">
        <PageHeader
          eyebrow="Event Studio"
          title={title}
          description={description}
          actions={actions}
        />

        <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
          <div className="rounded-[var(--radius-lg)] border border-border bg-card/90 px-4 py-3 shadow-[var(--shadow-soft)] backdrop-blur dark:bg-surface-elevated/90">
            <p className="text-sm text-muted-foreground">
              Step{" "}
              <span className="font-extrabold text-foreground">
                {stepIndex + 1}
              </span>{" "}
              of {STUDIO_STEPS.length}
              <span className="mx-2 text-border">·</span>
              <span className="font-semibold text-foreground">
                {stepMeta?.label}
              </span>
            </p>
            {stepMeta?.description ? (
              <p className="mt-0.5 text-xs text-muted-foreground">
                {stepMeta.description}
              </p>
            ) : null}
          </div>
          <UnsavedChangesBar
            dirty={dirty}
            lastSavedAt={lastSavedAt}
            saving={saving}
            onSave={onSaveDraft}
            className="sm:min-w-[260px]"
          />
        </div>
      </div>

      <div className="relative lg:hidden">
        <EventStudioStepper
          current={currentStep}
          completed={completed}
          onSelect={onStepChange}
          orientation="horizontal"
        />
      </div>

      <div className="relative grid gap-6 lg:grid-cols-[250px_minmax(0,1fr)] xl:grid-cols-[270px_minmax(0,1fr)]">
        <aside className="hidden min-w-0 lg:block">
          <div className="sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto pr-1">
            <EventStudioStepper
              current={currentStep}
              completed={completed}
              onSelect={onStepChange}
              orientation="vertical"
            />
          </div>
        </aside>

        <div
          key={currentStep}
          className="min-w-0 space-y-5 padeya-hero-brand"
        >
          {children}
          {footer}
        </div>
      </div>

      {mobileBar ? (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-card/95 px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur dark:bg-surface-elevated/95 lg:hidden">
          {mobileBar}
        </div>
      ) : null}
    </div>
  );
}
