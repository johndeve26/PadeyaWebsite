"use client";

import { Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";
import {
  formatAttachmentSize,
  isImageContentType,
} from "@/lib/messaging/attachment-limits";
import {
  deleteAdminAttachment,
  hideAdminAttachment,
  reviewAdminAttachment,
  restoreAdminAttachment,
} from "@/lib/messaging-api";
import type { MessageAttachment } from "@/lib/types/messaging";

export function AdminAttachmentModeration({
  attachment,
  onUpdated,
  onError,
  onSuccess,
}: {
  attachment: MessageAttachment;
  onUpdated: (next: MessageAttachment) => void;
  onError: (message: string) => void;
  onSuccess: (title: string) => void;
}) {
  const status = attachment.status || "ready";
  const href = attachment.url ? resolveMediaUrl(attachment.url) : "";
  const label = attachment.original_filename || "Attachment";
  async function run(
    action: () => Promise<{ status?: string; url?: string; reviewed_at?: string | null }>,
    title: string,
  ) {
    try {
      const res = await action();
      onUpdated({
        ...attachment,
        status: res.status || attachment.status,
        url: res.url ?? attachment.url,
        reviewed_at: res.reviewed_at ?? attachment.reviewed_at,
      });
      onSuccess(title);
    } catch (err) {
      onError(err instanceof ApiError ? err.detail : "Action failed");
    }
  }

  return (
    <div className="rounded-[var(--radius-md)] border border-border bg-surface-muted/60 px-2.5 py-2">
      <div className="flex min-w-0 flex-wrap items-start gap-2">
        {isImageContentType(attachment.content_type) && href ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={href}
            alt=""
            className="h-12 w-12 shrink-0 rounded object-cover"
          />
        ) : (
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded bg-background text-[10px] font-bold uppercase text-muted-foreground">
            File
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-foreground">{label}</p>
          <p className="text-xs text-muted-foreground">
            {status}
            {attachment.byte_size
              ? ` · ${formatAttachmentSize(attachment.byte_size)}`
              : ""}
            {attachment.reviewed_at ? " · reviewed" : ""}
          </p>
          {href && status !== "deleted" ? (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-semibold text-foreground underline underline-offset-2"
            >
              Open
            </a>
          ) : null}
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {status === "ready" ? (
          <Button
            size="sm"
            variant="danger"
            onClick={() =>
              void run(() => hideAdminAttachment(attachment.id), "Attachment hidden")
            }
          >
            Hide
          </Button>
        ) : null}
        {status === "hidden" || status === "deleted" || status === "rejected" ? (
          <Button
            size="sm"
            variant="secondary"
            onClick={() =>
              void run(
                () => restoreAdminAttachment(attachment.id),
                "Attachment restored",
              )
            }
          >
            Restore
          </Button>
        ) : null}
        {status !== "deleted" ? (
          <Button
            size="sm"
            variant="secondary"
            onClick={() =>
              void run(
                () => deleteAdminAttachment(attachment.id),
                "Attachment access disabled",
              )
            }
          >
            Disable access
          </Button>
        ) : null}
        <Button
          size="sm"
          variant="ghost"
          onClick={() =>
            void run(
              () => reviewAdminAttachment(attachment.id),
              "Attachment marked reviewed",
            )
          }
        >
          Mark reviewed
        </Button>
      </div>
    </div>
  );
}
