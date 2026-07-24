"use client";

import { Button } from "@/components/ui";

type Props = {
  saving: boolean;
  primaryLabel: string;
  draftLabel?: string;
  canPublish: boolean;
  onSaveDraft: () => void;
  onPublish: () => void;
  onPreview: () => void;
  showDraft?: boolean;
  /** Hide the desktop sticky bar when actions live in the page header. */
  desktopHidden?: boolean;
};

export function MerchStickyActions({
  saving,
  primaryLabel,
  draftLabel = "Save draft",
  canPublish,
  onSaveDraft,
  onPublish,
  onPreview,
  showDraft = true,
  desktopHidden = false,
}: Props) {
  return (
    <>
      {desktopHidden ? null : (
        <div className="sticky top-0 z-20 -mx-1 hidden border-b border-border bg-background/95 px-1 py-3 backdrop-blur md:block">
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onPreview}
            >
              Preview
            </Button>
            {showDraft ? (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={saving}
                onClick={onSaveDraft}
              >
                {saving ? "Saving…" : draftLabel}
              </Button>
            ) : null}
            <Button
              type="button"
              size="sm"
              disabled={saving || !canPublish}
              onClick={onPublish}
            >
              {saving ? "Saving…" : primaryLabel}
            </Button>
          </div>
        </div>
      )}

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 px-4 py-3 backdrop-blur md:hidden">
        <div className="mx-auto flex max-w-7xl items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="flex-1"
            onClick={onPreview}
          >
            Preview
          </Button>
          {showDraft ? (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="flex-1"
              disabled={saving}
              onClick={onSaveDraft}
            >
              Save
            </Button>
          ) : null}
          <Button
            type="button"
            size="sm"
            className="flex-1"
            disabled={saving || !canPublish}
            onClick={onPublish}
          >
            Publish
          </Button>
        </div>
      </div>
    </>
  );
}
