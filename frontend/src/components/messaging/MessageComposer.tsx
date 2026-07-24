"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

import { MessageEditComposer } from "@/components/messaging/MessageEditComposer";
import { MessagingPrivacyReminderBanner } from "@/components/messaging/MessagingPrivacyReminderBanner";
import { ReplyPreview } from "@/components/messaging/ReplyPreview";
import type {
  ComposerEditTarget,
  ComposerReplyTarget,
} from "@/components/messaging/composer-types";
import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  ATTACHMENT_ACCEPT,
  ATTACHMENT_MAX_COUNT,
  ATTACHMENT_MAX_TOTAL_BYTES,
  formatAttachmentSize,
  isImageContentType,
  mapAttachmentError,
  validateAttachmentFile,
} from "@/lib/messaging/attachment-limits";
import type { AttachmentUpload } from "@/lib/types/messaging";

export type { ComposerEditTarget, ComposerReplyTarget };

const MAX = 2000;

type PendingAttachment = {
  localId: string;
  serverId?: string;
  name: string;
  bytes: number;
  contentType: string;
  previewUrl?: string;
  progress: number;
  status: "uploading" | "ready" | "error";
  error?: string;
};

export function MessageComposer({
  disabled,
  disabledReason,
  privacyReminder,
  onSend,
  onUpload,
  onTyping,
  replyTo,
  onCancelReply,
  editTarget,
  onCancelEdit,
  onSaveEdit,
}: {
  disabled?: boolean;
  disabledReason?: string;
  privacyReminder: string;
  onSend: (body: string, attachmentIds: string[]) => Promise<void>;
  onUpload?: (
    file: File,
    onProgress?: (pct: number) => void,
  ) => Promise<AttachmentUpload>;
  onTyping?: (isTyping: boolean) => void;
  replyTo?: ComposerReplyTarget | null;
  onCancelReply?: () => void;
  editTarget?: ComposerEditTarget | null;
  onCancelEdit?: () => void;
  onSaveEdit?: (body: string) => Promise<void>;
}) {
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingAttachment[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const onTypingRef = useRef(onTyping);
  const pendingRef = useRef(pending);
  const inputId = useId();
  const editing = Boolean(editTarget);

  useEffect(() => {
    onTypingRef.current = onTyping;
  }, [onTyping]);

  useEffect(() => {
    pendingRef.current = pending;
  }, [pending]);

  useEffect(() => {
    if (!editTarget) return;
    queueMicrotask(() => {
      setBody(editTarget.body);
      setPending([]);
    });
  }, [editTarget]);

  const uploading = pending.some((p) => p.status === "uploading");
  const readyIds = pending
    .filter((p) => p.status === "ready" && p.serverId)
    .map((p) => p.serverId!);
  const pendingBytes = pending
    .filter((p) => p.status !== "error")
    .reduce((sum, m) => sum + m.bytes, 0);
  const attachDisabled =
    editing ||
    disabled ||
    sending ||
    uploading ||
    !onUpload ||
    pending.filter((p) => p.status !== "error").length >= ATTACHMENT_MAX_COUNT;
  const canSubmit =
    Boolean(body.trim() || (!editing && readyIds.length > 0)) &&
    !disabled &&
    !sending &&
    !uploading &&
    !pending.some((p) => p.status === "error");

  function notifyTyping(active: boolean) {
    onTypingRef.current?.(active);
  }

  useEffect(() => {
    return () => {
      notifyTyping(false);
      for (const item of pendingRef.current) {
        if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
      }
    };
  }, []);

  function removePending(localId: string) {
    setPending((items) => {
      const target = items.find((i) => i.localId === localId);
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
      return items.filter((i) => i.localId !== localId);
    });
    setError(null);
  }

  function handleComposerKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // WhatsApp-style: Enter sends, Shift+Enter adds a new line (Mac & Windows).
    if (e.key !== "Enter" || e.shiftKey || e.nativeEvent.isComposing) return;
    e.preventDefault();
    void submit();
  }

  async function submit() {
    if (!canSubmit) return;
    setSending(true);
    setError(null);
    try {
      notifyTyping(false);
      if (editing && onSaveEdit) {
        await onSaveEdit(body.trim());
        setBody("");
      } else {
        await onSend(body.trim(), readyIds);
        setBody("");
        setPending((items) => {
          for (const item of items) {
            if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
          }
          return [];
        });
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : editing
            ? "Could not save edit"
            : "Could not send",
      );
    } finally {
      setSending(false);
    }
  }

  async function onPick(fileList: FileList | null) {
    if (!fileList?.length || !onUpload || attachDisabled) return;
    const files = Array.from(fileList);
    if (fileRef.current) fileRef.current.value = "";

    let runningCount = pending.filter((p) => p.status !== "error").length;
    let runningBytes = pendingBytes;

    for (const file of files) {
      if (runningCount >= ATTACHMENT_MAX_COUNT) {
        setError(`At most ${ATTACHMENT_MAX_COUNT} files per message.`);
        break;
      }
      const typeError = validateAttachmentFile(file);
      if (typeError) {
        setError(typeError);
        continue;
      }
      if (runningBytes + file.size > ATTACHMENT_MAX_TOTAL_BYTES) {
        setError(
          `Attachments for one message must total ${formatAttachmentSize(ATTACHMENT_MAX_TOTAL_BYTES)} or less.`,
        );
        continue;
      }

      const localId = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
      const previewUrl = isImageContentType(file.type)
        ? URL.createObjectURL(file)
        : undefined;
      const row: PendingAttachment = {
        localId,
        name: file.name,
        bytes: file.size,
        contentType: file.type || "application/octet-stream",
        previewUrl,
        progress: 0,
        status: "uploading",
      };
      setPending((items) => [...items, row]);
      runningCount += 1;
      runningBytes += file.size;
      setError(null);

      try {
        const uploaded = await onUpload(file, (pct) => {
          setPending((items) =>
            items.map((i) =>
              i.localId === localId ? { ...i, progress: pct } : i,
            ),
          );
        });
        if (uploaded.status && uploaded.status !== "ready") {
          throw new Error("Attachment rejected.");
        }
        setPending((items) =>
          items.map((i) =>
            i.localId === localId
              ? {
                  ...i,
                  serverId: uploaded.id,
                  progress: 100,
                  status: "ready",
                  bytes: uploaded.byte_size || i.bytes,
                  contentType: uploaded.content_type || i.contentType,
                  name: uploaded.original_filename || i.name,
                }
              : i,
          ),
        );
      } catch (err) {
        const mapped = mapAttachmentError(err);
        setPending((items) =>
          items.map((i) =>
            i.localId === localId
              ? { ...i, status: "error", error: mapped, progress: 0 }
              : i,
          ),
        );
        setError(mapped);
      }
    }
  }

  return (
    <div className="z-10 shrink-0 space-y-2 border-t border-border bg-card p-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] dark:bg-surface-elevated md:p-3 md:pb-[max(0.75rem,env(safe-area-inset-bottom))]">
      <MessagingPrivacyReminderBanner text={privacyReminder} />
      {disabled && disabledReason ? (
        <p className="text-sm font-semibold text-danger">{disabledReason}</p>
      ) : null}

      {editing && editTarget ? (
        <MessageEditComposer
          editTarget={editTarget}
          onCancel={() => {
            onCancelEdit?.();
            setBody("");
          }}
        />
      ) : null}

      {!editing && replyTo ? (
        <ReplyPreview replyTo={replyTo} onCancel={onCancelReply} />
      ) : null}

      {pending.length > 0 ? (
        <ul className="flex max-w-full flex-wrap gap-2 overflow-x-auto pb-0.5">
          {pending.map((item) => (
            <li
              key={item.localId}
              className={cn(
                "relative min-w-0 max-w-[11rem] rounded-[var(--radius-md)] border px-2 py-1.5",
                item.status === "error"
                  ? "border-danger/40 bg-danger/5"
                  : "border-border bg-surface-muted",
              )}
            >
              <div className="flex items-start gap-2">
                {item.previewUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={item.previewUrl}
                    alt=""
                    className="h-10 w-10 shrink-0 rounded-[var(--radius-sm)] object-cover"
                  />
                ) : (
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-background text-[10px] font-bold uppercase text-muted-foreground">
                    File
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-foreground">
                    {item.name}
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    {formatAttachmentSize(item.bytes)}
                    {item.status === "uploading"
                      ? ` · ${item.progress}%`
                      : null}
                    {item.status === "error" ? " · Failed" : null}
                  </p>
                </div>
                <button
                  type="button"
                  className="shrink-0 rounded px-1 text-sm font-bold text-muted-foreground hover:text-foreground"
                  aria-label={`Remove ${item.name}`}
                  disabled={sending}
                  onClick={() => removePending(item.localId)}
                >
                  ×
                </button>
              </div>
              {item.status === "uploading" ? (
                <div
                  className="mt-1.5 h-1 overflow-hidden rounded-full bg-border"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={item.progress}
                >
                  <div
                    className="h-full bg-primary transition-[width] duration-150"
                    style={{ width: `${item.progress}%` }}
                  />
                </div>
              ) : null}
              {item.status === "error" && item.error ? (
                <p className="mt-1 text-[11px] font-semibold text-danger">
                  {item.error}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      <div className="flex items-end gap-2">
        <label htmlFor={inputId} className="sr-only">
          Message
        </label>
        <textarea
          id={inputId}
          value={body}
          onChange={(e) => {
            setBody(e.target.value.slice(0, MAX));
            if (!disabled && !sending && !uploading) notifyTyping(true);
          }}
          onBlur={() => notifyTyping(false)}
          onKeyDown={handleComposerKeyDown}
          rows={2}
          disabled={disabled || sending}
          placeholder="Write a message…"
          className="min-h-[2.75rem] min-w-0 flex-1 resize-none rounded-[var(--radius-md)] border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-focus-ring disabled:opacity-55"
        />
        <input
          ref={fileRef}
          type="file"
          accept={ATTACHMENT_ACCEPT}
          className="hidden"
          multiple
          disabled={attachDisabled}
          onChange={(e) => void onPick(e.target.files)}
        />
        {onUpload ? (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="shrink-0 px-3"
            disabled={attachDisabled}
            aria-label="Attach file"
            title={
              disabled
                ? disabledReason || "Attachments unavailable"
                : pending.filter((p) => p.status !== "error").length >=
                    ATTACHMENT_MAX_COUNT
                  ? `At most ${ATTACHMENT_MAX_COUNT} files`
                  : "Attach file"
            }
            onClick={() => fileRef.current?.click()}
          >
            <PaperclipIcon />
            <span className="hidden sm:inline">Attach</span>
          </Button>
        ) : null}
        <Button
          type="button"
          size="sm"
          className="shrink-0"
          disabled={!canSubmit}
          onClick={() => void submit()}
        >
          {sending
            ? editing
              ? "Saving…"
              : "Sending…"
            : editing
              ? "Save"
              : "Send"}
        </Button>
      </div>
      {error ? (
        <p className="text-sm font-semibold text-danger" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function PaperclipIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className="shrink-0"
    >
      <path
        d="M21 11.5 12.5 20a5 5 0 0 1-7-7l9-9a3.5 3.5 0 0 1 5 5l-9.2 9.2a2 2 0 0 1-2.8-2.8l8.2-8.2"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
