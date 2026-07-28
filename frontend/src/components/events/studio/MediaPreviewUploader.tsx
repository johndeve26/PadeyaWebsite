"use client";

import { useRef, useState } from "react";

import { Alert, Button, ConfirmAction, Input, Media, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  deleteEventMedia,
  uploadEventMediaFile,
  uploadHostMediaFile,
} from "@/lib/events-api";
import type { EventMedia } from "@/lib/types/events";

import { BrandAccentField } from "./BrandAccentField";
import { StudioFieldGroup, StudioMicrocopy } from "./studio-ui";

export type MediaFieldValues = {
  banner_url: string;
  mobile_banner_url: string;
  gallery_urls: string;
  teaser_video_url: string;
  sponsor_logo_urls: string;
  social_share_image_url: string;
  brand_accent_override: string;
};

function splitUrls(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function MediaUploadThumbnail({
  url,
  alt,
  className,
  emptyLabel = "No image yet",
  contain = false,
}: {
  url?: string;
  alt: string;
  className?: string;
  emptyLabel?: string;
  contain?: boolean;
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
          className={contain ? "h-full w-full object-contain p-1" : "h-full w-full object-cover"}
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

function ImageUploadField({
  label,
  hint,
  accept = "image/jpeg,image/png,image/webp,image/gif",
  uploading,
  previewUrl,
  previewAlt,
  previewClassName,
  previewEmptyLabel,
  previewContain = false,
  onPick,
}: {
  label: string;
  hint?: string;
  accept?: string;
  uploading: boolean;
  previewUrl?: string;
  previewAlt?: string;
  previewClassName?: string;
  previewEmptyLabel?: string;
  previewContain?: boolean;
  onPick: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <div className="flex gap-3">
      <MediaUploadThumbnail
        url={previewUrl}
        alt={previewAlt || label}
        className={previewClassName ?? "h-16 w-24"}
        emptyLabel={previewEmptyLabel}
        contain={previewContain}
      />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-sm font-semibold text-foreground">{label}</p>
            {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
          </div>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
          >
            {uploading ? "Uploading…" : "Upload image"}
          </Button>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="sr-only"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onPick(file);
            e.target.value = "";
          }}
        />
      </div>
    </div>
  );
}

export function MediaPreviewUploader({
  values,
  onChange,
  eventId,
  media = [],
}: {
  values: MediaFieldValues & { media_items?: EventMedia[] };
  onChange: (key: keyof MediaFieldValues, value: string) => void;
  eventId?: string;
  media?: EventMedia[];
}) {
  const [uploadingKey, setUploadingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const galleryLines = splitUrls(values.gallery_urls);
  const sponsorLines = splitUrls(values.sponsor_logo_urls);

  async function removeGalleryUrl(url: string) {
    const next = galleryLines.filter((line) => line !== url).join("\n");
    onChange("gallery_urls", next);
    if (!eventId) return;
    const match = media.find(
      (item) => item.media_type === "gallery" && item.url === url,
    );
    if (!match?.id) return;
    try {
      await deleteEventMedia(eventId, match.id);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Removed from list — save draft to sync if delete failed",
      );
    }
  }

  async function uploadToField(
    file: File,
    field: keyof MediaFieldValues,
    mediaType: string,
    options?: { appendGallery?: boolean; setAsBanner?: boolean },
  ) {
    setError(null);
    setUploadingKey(field);
    try {
      if (eventId) {
        const updated = await uploadEventMediaFile(eventId, file, {
          mediaType,
          setAsBanner: options?.setAsBanner || mediaType === "banner",
        });
        if (options?.appendGallery) {
          const latest = (updated.media ?? [])
            .filter((m) => m.media_type === "gallery")
            .map((m) => m.url)
            .join("\n");
          onChange("gallery_urls", latest || values.gallery_urls);
          return;
        }
        if (field === "sponsor_logo_urls") {
          const match = [...(updated.media ?? [])]
            .reverse()
            .find((m) => m.media_type === "sponsor" || m.media_type === mediaType);
          if (match) {
            const next = [values.sponsor_logo_urls.trim(), match.url]
              .filter(Boolean)
              .join("\n");
            onChange("sponsor_logo_urls", next);
          }
          return;
        }
        if (field === "banner_url" && updated.banner_url) {
          onChange("banner_url", updated.banner_url);
          return;
        }
        if (field === "mobile_banner_url" && updated.mobile_banner_url) {
          onChange("mobile_banner_url", updated.mobile_banner_url);
          return;
        }
        if (field === "social_share_image_url" && updated.social_share_image_url) {
          onChange("social_share_image_url", updated.social_share_image_url);
          return;
        }
        const match = [...(updated.media ?? [])]
          .reverse()
          .find((m) => m.media_type === mediaType);
        if (match) onChange(field, match.url);
        return;
      }

      const staged = await uploadHostMediaFile(file, mediaType);
      if (options?.appendGallery || field === "gallery_urls") {
        const next = [values.gallery_urls.trim(), staged.url]
          .filter(Boolean)
          .join("\n");
        onChange("gallery_urls", next);
      } else if (field === "sponsor_logo_urls") {
        const next = [values.sponsor_logo_urls.trim(), staged.url]
          .filter(Boolean)
          .join("\n");
        onChange("sponsor_logo_urls", next);
      } else {
        onChange(field, staged.url);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Unable to upload image");
    } finally {
      setUploadingKey(null);
    }
  }

  return (
    <div className="space-y-6">
      <StudioMicrocopy>
        Upload assets you own or host. Each field shows a thumbnail of what you
        added — use Preview in the header to see the full guest page.
      </StudioMicrocopy>

      {error ? (
        <Alert tone="danger" title="Upload failed">
          {error}
        </Alert>
      ) : null}

      <StudioFieldGroup
        title="Hero banner"
        description="Main listing hero — wide landscape (~21:9). JPEG, PNG, WebP, GIF, or SVG — max 5MB."
      >
        <ImageUploadField
          label="Banner image"
          hint="Prefer Upload, or paste a public URL below."
          previewUrl={values.banner_url}
          previewClassName="h-14 w-32"
          uploading={uploadingKey === "banner_url"}
          onPick={(file) =>
            void uploadToField(file, "banner_url", "banner", {
              setAsBanner: true,
            })
          }
        />
        <Input
          label="Banner URL"
          value={values.banner_url}
          onChange={(e) => onChange("banner_url", e.target.value)}
          placeholder="https://"
        />
      </StudioFieldGroup>

      <StudioFieldGroup
        title="Mobile banner"
        description="Optional taller crop for phones. If blank, the main banner is used."
      >
        <ImageUploadField
          label="Mobile banner"
          hint="Or paste a public URL below."
          previewUrl={values.mobile_banner_url || values.banner_url}
          previewClassName="h-20 w-14"
          previewEmptyLabel={
            values.banner_url.trim() ? "Uses main banner" : "No image yet"
          }
          uploading={uploadingKey === "mobile_banner_url"}
          onPick={(file) =>
            void uploadToField(file, "mobile_banner_url", "mobile_banner")
          }
        />
        <Input
          label="Mobile banner URL"
          value={values.mobile_banner_url}
          onChange={(e) => onChange("mobile_banner_url", e.target.value)}
          placeholder="https://"
        />
      </StudioFieldGroup>

      <StudioFieldGroup
        title="Gallery"
        description="Photo strip guests may see on the listing. Upload one image at a time."
      >
        <ImageUploadField
          label="Gallery image"
          hint="Appends to the gallery list below."
          previewUrl={galleryLines[0]}
          previewEmptyLabel="No images yet"
          uploading={uploadingKey === "gallery_urls"}
          onPick={(file) =>
            void uploadToField(file, "gallery_urls", "gallery", {
              appendGallery: true,
            })
          }
        />
        {galleryLines.length > 0 ? (
          <ul className="space-y-2">
            {galleryLines.map((url) => (
              <li
                key={url}
                className="flex items-center gap-3 rounded-[var(--radius-sm)] border border-border bg-surface-inset px-3 py-2"
              >
                <MediaUploadThumbnail
                  url={url}
                  alt=""
                  className="h-12 w-16"
                />
                <p className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
                  {url}
                </p>
                <ConfirmAction
                  label="Remove"
                  title="Remove this gallery image?"
                  description="Removes it from the listing. If already uploaded to this event, the media row is deleted now."
                  confirmLabel="Remove"
                  tone="danger"
                  variant="ghost"
                  size="sm"
                  onConfirm={() => removeGalleryUrl(url)}
                />
              </li>
            ))}
          </ul>
        ) : null}
        <Textarea
          label="Gallery URLs"
          hint="One image URL per line — edits sync on save."
          rows={3}
          value={values.gallery_urls}
          onChange={(e) => onChange("gallery_urls", e.target.value)}
          placeholder="https://"
        />
      </StudioFieldGroup>

      <StudioFieldGroup
        title="Teaser & social"
        description="Promo video and the image used when someone shares your link."
      >
        <div className="flex gap-3">
          <MediaUploadThumbnail
            url={undefined}
            alt="Teaser video"
            className="h-16 w-24"
            emptyLabel={
              values.teaser_video_url.trim() ? "Video link set" : "No video yet"
            }
          />
          <div className="min-w-0 flex-1">
            <Input
              label="Teaser video URL"
              hint="Optional YouTube, Vimeo, or direct video link."
              value={values.teaser_video_url}
              onChange={(e) => onChange("teaser_video_url", e.target.value)}
              placeholder="https://"
            />
          </div>
        </div>
        <ImageUploadField
          label="Social share image"
          hint="Square or ~1.91:1. Falls back to the banner if blank."
          previewUrl={values.social_share_image_url || values.banner_url}
          previewClassName="h-14 w-24"
          previewEmptyLabel={
            values.banner_url.trim() ? "Uses main banner" : "No image yet"
          }
          uploading={uploadingKey === "social_share_image_url"}
          onPick={(file) =>
            void uploadToField(file, "social_share_image_url", "social_share")
          }
        />
        <Input
          label="Social share image URL"
          value={values.social_share_image_url}
          onChange={(e) => onChange("social_share_image_url", e.target.value)}
          placeholder="https://"
        />
      </StudioFieldGroup>

      <StudioFieldGroup
        title="Sponsors & accent"
        description="Optional brand logos and a listing accent color."
      >
        <ImageUploadField
          label="Sponsor logo"
          hint="Appends to the sponsor list. Use your own brand assets only."
          previewUrl={sponsorLines[0]}
          previewClassName="h-12 w-20"
          previewEmptyLabel="No logos yet"
          previewContain
          uploading={uploadingKey === "sponsor_logo_urls"}
          onPick={(file) =>
            void uploadToField(file, "sponsor_logo_urls", "sponsor")
          }
        />
        {sponsorLines.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {sponsorLines.map((url) => (
              <MediaUploadThumbnail
                key={url}
                url={url}
                alt=""
                className="h-10 w-16"
                contain
              />
            ))}
          </div>
        ) : null}
        <Textarea
          label="Sponsor logo URLs"
          hint="One logo URL per line."
          rows={2}
          value={values.sponsor_logo_urls}
          onChange={(e) => onChange("sponsor_logo_urls", e.target.value)}
          placeholder="https://"
        />
        <BrandAccentField
          value={values.brand_accent_override}
          onChange={(next) => onChange("brand_accent_override", next)}
        />
      </StudioFieldGroup>

      {!eventId ? (
        <StudioMicrocopy>
          Images upload immediately and stay attached when you save this draft.
        </StudioMicrocopy>
      ) : null}
    </div>
  );
}
