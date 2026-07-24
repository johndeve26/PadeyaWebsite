"use client";

import { cn } from "@/lib/cn";
import { resolveMediaUrl } from "@/lib/media";
import {
  documentKindLabel,
  formatAttachmentSize,
  isImageContentType,
} from "@/lib/messaging/attachment-limits";
import type { MessageAttachment } from "@/lib/types/messaging";

export function MessageAttachmentBlock({
  attachment,
  mine,
}: {
  attachment: MessageAttachment;
  mine?: boolean;
}) {
  const label =
    attachment.original_filename ||
    (isImageContentType(attachment.content_type) ? "Image" : "Attachment");
  const href = attachment.url ? resolveMediaUrl(attachment.url) : "";
  const size = attachment.byte_size
    ? formatAttachmentSize(attachment.byte_size)
    : null;
  const kind = documentKindLabel(attachment.content_type);

  const muted = mine
    ? "text-primary-foreground/75"
    : "text-muted-foreground";
  const strong = mine ? "text-primary-foreground" : "text-foreground";
  const surface = mine
    ? "bg-primary-foreground/12 border-primary-foreground/25"
    : "bg-background/80 border-border";

  if (isImageContentType(attachment.content_type) && href) {
    return (
      <figure className="min-w-0 max-w-full space-y-1.5">
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="block min-w-0 overflow-hidden rounded-[var(--radius-md)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
          aria-label={`Open ${label}`}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={href}
            alt={label}
            className="max-h-52 w-auto max-w-full object-contain"
          />
        </a>
        <figcaption className={cn("min-w-0 text-xs", muted)}>
          <span className={cn("block truncate font-semibold", strong)}>
            {label}
          </span>
          {size ? <span>{size}</span> : null}
        </figcaption>
      </figure>
    );
  }

  return (
    <div
      className={cn(
        "flex min-w-0 max-w-full items-center gap-2.5 rounded-[var(--radius-md)] border px-2.5 py-2",
        surface,
      )}
    >
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[10px] font-bold uppercase tracking-wide",
          mine
            ? "bg-primary-foreground/20 text-primary-foreground"
            : "bg-surface-muted text-foreground",
        )}
        aria-hidden
      >
        {kind.slice(0, 4)}
      </div>
      <div className="min-w-0 flex-1">
        <p className={cn("truncate text-sm font-semibold", strong)}>{label}</p>
        <p className={cn("text-xs", muted)}>
          {kind}
          {size ? ` · ${size}` : ""}
        </p>
      </div>
      {href ? (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            "shrink-0 rounded-[var(--radius-sm)] px-2 py-1 text-xs font-bold underline-offset-2 hover:underline",
            strong,
          )}
        >
          {isImageContentType(attachment.content_type) ? "Open" : "Download"}
        </a>
      ) : (
        <span className={cn("shrink-0 text-xs font-semibold", muted)}>
          Unavailable
        </span>
      )}
    </div>
  );
}
