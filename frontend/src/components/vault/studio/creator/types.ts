import type { VaultItemEditorValues } from "@/components/vault/studio/VaultItemEditor";
import type { VaultItem, VaultMediaDraft } from "@/lib/types/vault";

export const VAULT_CREATOR_STEPS = [
  {
    id: "content",
    label: "Content",
    description: "Title, type, teaser, and exclusive body",
  },
  {
    id: "media",
    label: "Media",
    description: "Cover, gallery, files, and links",
  },
  {
    id: "access",
    label: "Access",
    description: "Who can unlock this drop",
  },
  {
    id: "related",
    label: "Related Event",
    description: "Link event, memory, and Legacy",
  },
  {
    id: "publish",
    label: "Preview & Publish",
    description: "Check previews and go live",
  },
] as const;

export type VaultCreatorStepId = (typeof VAULT_CREATOR_STEPS)[number]["id"];

export type VaultPublishChecklistItem = {
  id: string;
  label: string;
  done: boolean;
  required: boolean;
};

export function parseVaultCreatorStep(
  value: string | null | undefined,
): VaultCreatorStepId {
  const match = VAULT_CREATOR_STEPS.find((s) => s.id === value);
  return match?.id ?? "content";
}

export function slugifyTitle(title: string): string {
  return title
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

export function getPrimaryMediaUrl(
  media: VaultMediaDraft[],
  mediaType: string,
): string {
  return media.find((m) => m.media_type === mediaType)?.url || "";
}

export function setPrimaryMediaUrl(
  media: VaultMediaDraft[],
  mediaType: string,
  url: string,
): VaultMediaDraft[] {
  const trimmed = url.trim();
  const index = media.findIndex((m) => m.media_type === mediaType);
  if (!trimmed) {
    if (index < 0) return media;
    return media.filter((_, i) => i !== index).map((m, i) => ({ ...m, sort_order: i }));
  }
  if (index >= 0) {
    return media.map((m, i) => (i === index ? { ...m, url: trimmed } : m));
  }
  return [
    ...media,
    {
      url: trimmed,
      media_type: mediaType,
      label: mediaType,
      is_preview: false,
      sort_order: media.length,
    },
  ];
}

export function vaultCreatorStepCompletion(
  values: VaultItemEditorValues,
): Record<VaultCreatorStepId, boolean> {
  const needsFile = values.content_type === "file_download";
  const needsExternal = values.content_type === "external_link";
  const access = values.access;
  const inviteOk =
    access.access_type !== "invite_only" || Boolean(access.access_code.trim());
  const paidOk =
    access.access_type !== "one_time_unlock" || Number(access.price || 0) > 0;

  return {
    content: Boolean(
      values.title.trim().length >= 2 &&
        values.content_type &&
        (values.preview_text.trim() || values.description.trim() || values.body.trim()),
    ),
    media: Boolean(
      values.cover_url.trim() ||
        values.media.some((m) => m.url.trim()) ||
        values.file_url.trim() ||
        values.external_url.trim() ||
        (!needsFile && !needsExternal),
    ),
    access: inviteOk && paidOk,
    related: true,
    publish: Boolean(values.title.trim().length >= 2),
  };
}

export function buildVaultPublishChecklist(
  values: VaultItemEditorValues,
  options: { previewChecked: boolean },
): VaultPublishChecklistItem[] {
  const { previewChecked } = options;
  const access = values.access;
  const needsFile = values.content_type === "file_download";
  const needsExternal = values.content_type === "external_link";
  const inviteOk =
    access.access_type !== "invite_only" || Boolean(access.access_code.trim());
  const paidOk =
    access.access_type !== "one_time_unlock" || Number(access.price || 0) > 0;

  return [
    {
      id: "title",
      label: "Title is set",
      done: values.title.trim().length >= 2,
      required: true,
    },
    {
      id: "teaser",
      label: "Teaser or description for the public catalog",
      done: Boolean(values.preview_text.trim() || values.description.trim()),
      required: true,
    },
    {
      id: "body",
      label: "Exclusive body, file, media, or external link",
      done: Boolean(
        values.body.trim() ||
          values.file_url.trim() ||
          values.external_url.trim() ||
          values.media.some((m) => m.url.trim()),
      ),
      required: true,
    },
    {
      id: "file",
      label: "File URL for download drop",
      done: !needsFile || Boolean(values.file_url.trim()),
      required: needsFile,
    },
    {
      id: "external",
      label: "External URL for link drop",
      done: !needsExternal || Boolean(values.external_url.trim()),
      required: needsExternal,
    },
    {
      id: "access",
      label: "Access rules are valid",
      done: inviteOk && paidOk,
      required: true,
    },
    {
      id: "cover",
      label: "Cover image (recommended)",
      done: Boolean(values.cover_url.trim()),
      required: false,
    },
    {
      id: "preview",
      label: "Reviewed public / locked / unlock previews",
      done: previewChecked,
      required: true,
    },
  ];
}

export function valuesToDraftPreviewItem(
  values: VaultItemEditorValues,
  mode: "public" | "locked" | "unlock",
): VaultItem {
  const price = Number(values.access.price || 0);
  const locked = mode !== "unlock";
  const media = values.media
    .filter((m) => m.url.trim())
    .filter((m) => mode === "unlock" || m.is_preview)
    .map((m, index) => ({
      id: `draft-${index}`,
      media_type: m.media_type,
      url: m.url,
      label: m.label || null,
      is_preview: m.is_preview,
      sort_order: index,
      locked: locked && !m.is_preview,
    }));

  return {
    id: "draft-preview",
    host_id: "",
    host_username: "you",
    host_display_name: "You",
    title: values.title.trim() || "Untitled drop",
    slug: values.slug.trim() || slugifyTitle(values.title) || "untitled",
    content_type: values.content_type,
    status: values.status || "draft",
    description: values.description || null,
    preview_text: values.preview_text || null,
    body: locked ? null : values.body || null,
    cover_url: values.cover_url || null,
    file_url: locked ? null : values.file_url || null,
    external_url: locked ? null : values.external_url || null,
    related_event_id: values.related_event_id || null,
    related_memory_id: values.related_memory_id || null,
    tags: values.tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean),
    price,
    currency: values.access.currency || "NGN",
    moderation_status: "none",
    published_at: null,
    expires_at: null,
    created_at: new Date().toISOString(),
    access: {
      access_type: values.access.access_type,
      price,
      currency: values.access.currency || "NGN",
      required_event_id: values.access.required_event_id || null,
      event_id: values.access.required_event_id || null,
      required_ticket_type_id: values.access.required_ticket_type_id || null,
      ticket_type_ids: values.access.required_ticket_type_id
        ? [values.access.required_ticket_type_id]
        : null,
      require_check_in: values.access.require_check_in,
      required_legacy_tier: values.access.required_legacy_tier || null,
      access_code: null,
      access_code_set: Boolean(values.access.access_code.trim()),
      max_unlocks: values.access.max_unlocks
        ? Number(values.access.max_unlocks)
        : null,
      starts_at: values.access.starts_at || null,
      ends_at: values.access.ends_at || null,
    },
    media,
    has_access: !locked,
    access_reason: locked ? "preview" : "owner",
    lock_reason: locked ? "Access required" : null,
    locked,
    expired: false,
    share_path: `/@you/vault/${values.slug.trim() || "untitled"}`,
    cta_label: locked ? "Unlock" : null,
  };
}
