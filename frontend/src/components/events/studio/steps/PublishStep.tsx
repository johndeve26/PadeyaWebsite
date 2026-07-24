"use client";

import Link from "next/link";

import { Alert, Button, ConfirmAction } from "@/components/ui";
import type { EventPublishChecklist } from "@/lib/types/events";

import { missingChecklistLabels } from "../checklist-utils";
import { EventStudioSection } from "../EventStudioSection";
import { PublishChecklist } from "../PublishChecklist";
import type { EventStudioValues } from "../types";

export function PublishStep({
  values,
  checklist,
  eventId,
  eventStatus,
  previewing,
  saving,
  canPublish = false,
  canArchiveDraft = false,
  canDeleteDraft = false,
  onPreviewChecked,
  onOpenPreview,
  onSaveDraft,
  onSubmitReview,
  onPublish,
  onArchiveDraft,
  onDeleteDraft,
}: {
  values: EventStudioValues;
  checklist: EventPublishChecklist;
  eventId?: string;
  eventStatus?: string | null;
  previewing: boolean;
  saving: boolean;
  canPublish?: boolean;
  canArchiveDraft?: boolean;
  canDeleteDraft?: boolean;
  onPreviewChecked: (value: boolean) => void;
  onOpenPreview: () => void;
  onSaveDraft: () => void;
  onSubmitReview: () => void;
  onPublish?: () => void;
  onArchiveDraft?: () => void | Promise<void>;
  onDeleteDraft?: () => void | Promise<void>;
}) {
  const missing = missingChecklistLabels(checklist);
  const ready = checklist.ready_to_submit;
  const isDraftLike =
    !eventStatus || eventStatus === "draft" || eventStatus === "rejected";

  return (
    <EventStudioSection
      title="Preview & Publish"
      description="Work through the checklist, preview the guest page, then save, submit, or publish when your role allows."
    >
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="secondary"
          disabled={saving}
          onClick={onSaveDraft}
        >
          {saving ? "Saving…" : "Save draft"}
        </Button>
        <Button
          type="button"
          disabled={previewing || saving}
          onClick={onOpenPreview}
        >
          {previewing ? "Opening preview…" : "Preview event"}
        </Button>
        <ConfirmAction
          label="Publish event"
          title="Publish this event?"
          description="Your listing goes live on Pàdéyá immediately. Our team may review it after publish."
          confirmLabel="Publish event"
          disabled={saving || !ready}
          onConfirm={onSubmitReview}
        />
        {canPublish && onPublish ? (
          <ConfirmAction
            label="Publish now"
            title="Publish this event now?"
            description="Same as Publish event — your listing becomes public immediately."
            confirmLabel="Publish now"
            disabled={saving || !ready}
            onConfirm={onPublish}
          />
        ) : null}
      </div>

      {!ready && missing.length > 0 ? (
        <Alert tone="warning" title="Finish the checklist first">
          {missing.join(" · ")}
        </Alert>
      ) : null}

      {canPublish ? (
        <p className="text-sm text-muted-foreground">
          Your role can publish directly after the checklist is complete.
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">
          Publish goes live immediately. Pàdéyá may review listings after they
          are public.
        </p>
      )}

      <PublishChecklist
        checklist={checklist}
        previewChecked={values.preview_checked}
        onPreviewChecked={onPreviewChecked}
      />

      {(canArchiveDraft || canDeleteDraft) && isDraftLike && eventId ? (
        <div className="flex flex-wrap gap-2 border-t border-border pt-4">
          {canArchiveDraft && onArchiveDraft ? (
            <ConfirmAction
              label="Archive draft"
              title="Archive this draft?"
              description="The draft stays in the system as archived (not deleted). You can find it later from Host → Events if archived events are shown."
              confirmLabel="Archive draft"
              disabled={saving}
              onConfirm={onArchiveDraft}
            />
          ) : null}
          {canDeleteDraft && onDeleteDraft ? (
            <ConfirmAction
              label="Delete draft"
              title="Delete this draft permanently?"
              description="Only safe for drafts/rejected events with no ticket sales. This cannot be undone."
              confirmLabel="Delete permanently"
              tone="danger"
              disabled={saving}
              onConfirm={onDeleteDraft}
            />
          ) : null}
        </div>
      ) : null}

      <div className="rounded-[var(--radius-md)] border border-border bg-muted/60 px-4 py-3 text-sm text-muted-foreground">
        <p className="font-semibold text-foreground">Also available</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>Save as template — Host → Templates after you save</li>
          {eventId ? (
            <li>
              Manage inventory on{" "}
              <Link
                href={`/host/events/${eventId}/tickets`}
                className="font-semibold text-foreground underline-offset-2 hover:underline"
              >
                Tickets
              </Link>{" "}
              after save
            </li>
          ) : null}
          {eventId ? (
            <li>
              Full lifecycle controls on the{" "}
              <Link
                href={`/host/events/${eventId}`}
                className="font-semibold text-foreground underline-offset-2 hover:underline"
              >
                event detail
              </Link>{" "}
              page
            </li>
          ) : null}
        </ul>
      </div>
    </EventStudioSection>
  );
}
