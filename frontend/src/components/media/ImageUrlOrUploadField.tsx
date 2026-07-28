"use client";

import { useRef, useState } from "react";

import { Alert, Button, Input, Media, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { splitImageUrlLines, uploadFormImage } from "@/lib/media-upload";

const DEFAULT_ACCEPT =
  "image/jpeg,image/png,image/webp,image/gif";

function ImagePreview({
  url,
  alt,
  className,
  contain = false,
  emptyLabel = "No image yet",
}: {
  url?: string;
  alt: string;
  className?: string;
  contain?: boolean;
  emptyLabel?: string;
}) {
  const hasUrl = Boolean(url?.trim());
  return (
    <div
      className={`relative shrink-0 overflow-hidden rounded-[var(--radius-sm)] border border-border bg-surface-inset ${className ?? ""}`}
    >
      {hasUrl ? (
        <Media
          src={url!}
          alt={alt}
          className={
            contain
              ? "h-full w-full object-contain p-1"
              : "h-full w-full object-cover"
          }
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center p-2">
          <p className="text-center text-[10px] leading-tight text-muted-foreground">
            {emptyLabel}
          </p>
        </div>
      )}
    </div>
  );
}

export function ImageUrlOrUploadField({
  label,
  hint,
  value,
  onChange,
  eventId,
  mediaType = "other",
  setAsBanner = false,
  accept = DEFAULT_ACCEPT,
  disabled = false,
  showPreview = true,
  previewClassName = "h-16 w-16",
  previewContain = false,
  previewEmptyLabel = "No image yet",
  showUrlInput = true,
  urlInputLabel = "Or paste URL",
  urlPlaceholder = "https://",
  showClear = true,
  onUploaded,
  /** Force account-level avatar upload (fans + hosts). Overrides host media staging. */
  accountAvatar = false,
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (url: string) => void;
  eventId?: string;
  mediaType?: string;
  setAsBanner?: boolean;
  accept?: string;
  disabled?: boolean;
  showPreview?: boolean;
  previewClassName?: string;
  previewContain?: boolean;
  previewEmptyLabel?: string;
  showUrlInput?: boolean;
  urlInputLabel?: string;
  urlPlaceholder?: string;
  showClear?: boolean;
  onUploaded?: (url: string) => void;
  accountAvatar?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const useAccountAvatar =
    accountAvatar || mediaType === "avatar" || mediaType === "logo";

  async function onPick(file: File) {
    setError(null);
    setUploading(true);
    try {
      const url = await uploadFormImage(file, {
        eventId: useAccountAvatar ? undefined : eventId,
        mediaType: useAccountAvatar ? "avatar" : mediaType,
        setAsBanner: useAccountAvatar ? false : setAsBanner,
        accountAvatar: useAccountAvatar,
      });
      onChange(url);
      onUploaded?.(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Unable to upload image");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-2">
      <div className={showPreview ? "flex gap-3" : undefined}>
        {showPreview ? (
          <ImagePreview
            url={value}
            alt={label}
            className={previewClassName}
            contain={previewContain}
            emptyLabel={previewEmptyLabel}
          />
        ) : null}
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-foreground">{label}</p>
              {hint ? (
                <p className="text-xs text-muted-foreground">{hint}</p>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={disabled || uploading}
                onClick={() => inputRef.current?.click()}
              >
                {uploading ? "Uploading…" : "Upload image"}
              </Button>
              {showClear && value.trim() ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={disabled || uploading}
                  onClick={() => onChange("")}
                >
                  Clear
                </Button>
              ) : null}
            </div>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            className="sr-only"
            disabled={disabled || uploading}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void onPick(file);
              e.target.value = "";
            }}
          />
        </div>
      </div>

      {error ? (
        <Alert tone="danger" title="Upload failed">
          {error}
        </Alert>
      ) : null}

      {showUrlInput ? (
        <Input
          label={urlInputLabel}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={urlPlaceholder}
          disabled={disabled || uploading}
        />
      ) : null}
    </div>
  );
}

export function ImageUrlListUploadField({
  label,
  hint,
  value,
  onChange,
  eventId,
  mediaType = "gallery",
  disabled = false,
  rows = 3,
  urlInputLabel = "Image URLs",
  urlHint = "One URL per line — edits sync on save.",
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  eventId?: string;
  mediaType?: string;
  disabled?: boolean;
  rows?: number;
  urlInputLabel?: string;
  urlHint?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lines = splitImageUrlLines(value);

  async function onPick(file: File) {
    setError(null);
    setUploading(true);
    try {
      const url = await uploadFormImage(file, { eventId, mediaType });
      onChange([value.trim(), url].filter(Boolean).join("\n"));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Unable to upload image");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-3">
        <ImagePreview
          url={lines[0]}
          alt={label}
          className="h-16 w-16"
          emptyLabel="No images yet"
        />
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-foreground">{label}</p>
              {hint ? (
                <p className="text-xs text-muted-foreground">{hint}</p>
              ) : null}
            </div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={disabled || uploading}
              onClick={() => inputRef.current?.click()}
            >
              {uploading ? "Uploading…" : "Upload image"}
            </Button>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={DEFAULT_ACCEPT}
            className="sr-only"
            disabled={disabled || uploading}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void onPick(file);
              e.target.value = "";
            }}
          />
        </div>
      </div>

      {error ? (
        <Alert tone="danger" title="Upload failed">
          {error}
        </Alert>
      ) : null}

      {lines.length > 0 ? (
        <ul className="flex flex-wrap gap-2">
          {lines.map((url) => (
            <li
              key={url}
              className="h-16 w-16 overflow-hidden rounded-[var(--radius-sm)] border border-border bg-surface-muted"
            >
              <Media src={url} alt="" className="h-full w-full object-cover" />
            </li>
          ))}
        </ul>
      ) : null}

      <Textarea
        label={urlInputLabel}
        hint={urlHint}
        rows={rows}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || uploading}
        placeholder="https://"
      />
    </div>
  );
}
