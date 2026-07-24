"use client";

import type { VaultItemEditorValues } from "@/components/vault/studio/VaultItemEditor";
import { VaultMediaEditor } from "@/components/vault/studio/VaultMediaEditor";
import { ImageUrlOrUploadField } from "@/components/media/ImageUrlOrUploadField";
import { Input } from "@/components/ui";

import { getPrimaryMediaUrl, setPrimaryMediaUrl } from "../types";

type Props = {
  values: VaultItemEditorValues;
  onChange: (next: VaultItemEditorValues) => void;
};

export function MediaStep({ values, onChange }: Props) {
  const needsFile =
    values.content_type === "file_download" ||
    values.content_type === "discount_drop";
  const needsExternal = values.content_type === "external_link";
  const videoUrl = getPrimaryMediaUrl(values.media, "video");
  const audioUrl = getPrimaryMediaUrl(values.media, "audio");

  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <h2 className="text-xl font-extrabold text-foreground">Media</h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Cover and preview assets stay visible when locked. Private media, file
          URLs, and external links stay protected.
        </p>
      </div>

      <ImageUrlOrUploadField
        label="Cover image"
        hint="Hero image for catalog cards and Legacy Vault preview."
        value={values.cover_url}
        onChange={(url) => onChange({ ...values, cover_url: url })}
        mediaType="other"
        previewClassName="h-16 w-24"
      />

      <VaultMediaEditor
        value={values.media}
        onChange={(media) => onChange({ ...values, media })}
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Video URL"
          value={videoUrl}
          onChange={(e) =>
            onChange({
              ...values,
              media: setPrimaryMediaUrl(values.media, "video", e.target.value),
            })
          }
          placeholder="https://"
          hint="Primary video asset (stored as private media unless marked preview)."
        />
        <Input
          label="Audio URL"
          value={audioUrl}
          onChange={(e) =>
            onChange({
              ...values,
              media: setPrimaryMediaUrl(values.media, "audio", e.target.value),
            })
          }
          placeholder="https://"
          hint="Primary audio asset for sets, interviews, or soundtracks."
        />
      </div>

      <Input
        label="File URL"
        value={values.file_url}
        onChange={(e) => onChange({ ...values, file_url: e.target.value })}
        placeholder="https://"
        hint="Primary download for file_download / discount assets. Locked without access."
        required={values.content_type === "file_download"}
      />

      <Input
        label="External URL"
        value={values.external_url}
        onChange={(e) => onChange({ ...values, external_url: e.target.value })}
        placeholder="https://"
        hint={
          needsExternal
            ? "Required for external_link drops — revealed after unlock."
            : "Optional private link revealed after unlock."
        }
        required={needsExternal}
      />

      {needsFile && !values.file_url.trim() ? (
        <p className="text-sm text-warning">
          Add a file URL before publishing this content type.
        </p>
      ) : null}
    </div>
  );
}
