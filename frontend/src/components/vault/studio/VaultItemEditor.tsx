"use client";

import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";

import { VaultAccessRuleEditor } from "@/components/vault/studio/VaultAccessRuleEditor";
import { VaultMediaEditor } from "@/components/vault/studio/VaultMediaEditor";
import { ImageUrlOrUploadField } from "@/components/media/ImageUrlOrUploadField";
import { Alert, Button, Card, Input, Select, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMyEvents } from "@/lib/events-api";
import {
  clearLegacyFeaturedPlacement,
  upsertLegacyFeaturedItem,
} from "@/lib/legacy-api";
import { fetchHostMemory } from "@/lib/memories-api";
import type { EventItem } from "@/lib/types/events";
import {
  CONTENT_TYPE_HINTS,
  CONTENT_TYPES,
  type VaultAccessDraft,
  type VaultItem,
  type VaultMediaDraft,
} from "@/lib/types/vault";

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

function toDatetimeLocal(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function fromDatetimeLocal(value: string): string | null {
  if (!value.trim()) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function FormSection({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <fieldset className="space-y-4 border-b border-border pb-8 last:border-b-0 last:pb-0">
      <legend className="sr-only">{title}</legend>
      <div className="space-y-1">
        <h3 className="text-lg font-extrabold text-foreground">{title}</h3>
        {description ? (
          <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <div className="space-y-4">{children}</div>
    </fieldset>
  );
}

export type VaultItemEditorValues = {
  title: string;
  slug: string;
  content_type: string;
  description: string;
  preview_text: string;
  body: string;
  cover_url: string;
  file_url: string;
  external_url: string;
  related_event_id: string;
  related_memory_id: string;
  tags: string;
  status: string;
  expires_at: string;
  access: VaultAccessDraft;
  media: VaultMediaDraft[];
  feature_on_legacy: boolean;
};

function emptyAccessDraft(): VaultAccessDraft {
  return {
    access_type: "free",
    price: "0",
    currency: "NGN",
    required_event_id: "",
    required_ticket_type_id: "",
    require_check_in: false,
    required_legacy_tier: "",
    access_code: "",
    max_unlocks: "",
    starts_at: "",
    ends_at: "",
  };
}

export function valuesFromItem(item: VaultItem): VaultItemEditorValues {
  const accessPrice = item.access?.price ?? item.price ?? 0;
  return {
    title: item.title,
    slug: item.slug,
    content_type: item.content_type,
    description: item.description || "",
    preview_text: item.preview_text || "",
    body: item.body || "",
    cover_url: item.cover_url || "",
    file_url: item.file_url || "",
    external_url: item.external_url || "",
    related_event_id: item.related_event_id || "",
    related_memory_id: item.related_memory_id || "",
    tags: (item.tags || []).join(", "),
    status: item.status,
    expires_at: toDatetimeLocal(item.expires_at),
    access: {
      access_type: item.access?.access_type || "free",
      price: String(accessPrice),
      currency: item.access?.currency || item.currency || "NGN",
      required_event_id:
        item.access?.required_event_id || item.access?.event_id || "",
      required_ticket_type_id: item.access?.required_ticket_type_id || "",
      require_check_in: Boolean(item.access?.require_check_in),
      required_legacy_tier: item.access?.required_legacy_tier || "",
      // Codes are hashed server-side and never returned — blank means keep existing
      access_code: "",
      max_unlocks:
        item.access?.max_unlocks != null ? String(item.access.max_unlocks) : "",
      starts_at: toDatetimeLocal(item.access?.starts_at),
      ends_at: toDatetimeLocal(item.access?.ends_at),
    },
    media: (item.media || [])
      .filter((m) => m.url)
      .map((m, index) => ({
        url: m.url || "",
        media_type: m.media_type,
        label: m.label || "",
        is_preview: m.is_preview,
        sort_order: m.sort_order ?? index,
      })),
    feature_on_legacy: false,
  };
}

export function emptyVaultValues(): VaultItemEditorValues {
  return {
    title: "",
    slug: "",
    content_type: "text_post",
    description: "",
    preview_text: "",
    body: "",
    cover_url: "",
    file_url: "",
    external_url: "",
    related_event_id: "",
    related_memory_id: "",
    tags: "",
    status: "draft",
    expires_at: "",
    access: emptyAccessDraft(),
    media: [],
    feature_on_legacy: false,
  };
}

export function toVaultPayload(values: VaultItemEditorValues) {
  const tags = values.tags
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
  const price = Number(values.access.price || 0);
  return {
    title: values.title,
    slug: values.slug || undefined,
    content_type: values.content_type,
    description: values.description || null,
    preview_text: values.preview_text || null,
    body: values.body || null,
    cover_url: values.cover_url || null,
    file_url: values.file_url || null,
    external_url: values.external_url || null,
    related_event_id: values.related_event_id || null,
    related_memory_id: values.related_memory_id || null,
    tags: tags.length > 0 ? tags : null,
    price,
    currency: values.access.currency || "NGN",
    status: values.status,
    expires_at: fromDatetimeLocal(values.expires_at),
    access: {
      access_type: values.access.access_type,
      price,
      currency: values.access.currency || "NGN",
      required_event_id: values.access.required_event_id || null,
      required_ticket_type_id: values.access.required_ticket_type_id || null,
      require_check_in:
        values.access.access_type === "checked_in_attendee_only"
          ? true
          : values.access.require_check_in,
      required_legacy_tier: values.access.required_legacy_tier || null,
      // Only send when host sets/rotates a code — blank keeps the hashed secret
      ...(values.access.access_code.trim()
        ? { access_code: values.access.access_code.trim() }
        : {}),
      max_unlocks: values.access.max_unlocks
        ? Number(values.access.max_unlocks)
        : null,
      starts_at: fromDatetimeLocal(values.access.starts_at),
      ends_at: fromDatetimeLocal(values.access.ends_at),
    },
    media: values.media
      .filter((m) => m.url.trim())
      .map((m, index) => ({
        url: m.url.trim(),
        media_type: m.media_type || "file",
        label: m.label || null,
        is_preview: m.is_preview,
        sort_order: index,
      })),
  };
}

type MemoryOption = { id: string; label: string };

type Props = {
  initial: VaultItemEditorValues;
  mode: "create" | "edit";
  itemId?: string;
  submitLabel: string;
  onSubmit: (payload: Record<string, unknown>) => Promise<VaultItem>;
  onSaved?: (item: VaultItem) => void;
  secondaryActions?: ReactNode;
};

export function VaultItemEditor({
  initial,
  mode,
  itemId,
  submitLabel,
  onSubmit,
  onSaved,
  secondaryActions,
}: Props) {
  const [values, setValues] = useState(initial);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [memories, setMemories] = useState<MemoryOption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const needsFile =
    values.content_type === "file_download" || values.content_type === "discount_drop";
  const needsExternal = values.content_type === "external_link";

  const memoryEventIds = useMemo(
    () =>
      values.related_event_id
        ? [values.related_event_id]
        : events.slice(0, 12).map((event) => event.id),
    [events, values.related_event_id],
  );

  const memoriesForSelect = useMemo(
    () => (memoryEventIds.length === 0 ? [] : memories),
    [memoryEventIds, memories],
  );

  useEffect(() => {
    let active = true;
    void fetchMyEvents()
      .then((rows) => {
        if (active) setEvents(rows);
      })
      .catch(() => {
        if (active) setEvents([]);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (memoryEventIds.length === 0) return;
    let active = true;

    void (async () => {
      const options: MemoryOption[] = [];
      await Promise.all(
        memoryEventIds.map(async (eventId) => {
          try {
            const memory = await fetchHostMemory(eventId);
            const event = events.find((e) => e.id === eventId);
            options.push({
              id: memory.id,
              label: event?.title || memory.event_title || "Event memory",
            });
          } catch {
            // Event has no memory yet
          }
        }),
      );
      if (active) setMemories(options);
    })();

    return () => {
      active = false;
    };
  }, [events, memoryEventIds]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const item = await onSubmit(toVaultPayload(values));
      if (values.feature_on_legacy && item.id) {
        await upsertLegacyFeaturedItem({
          item_type: "vault_item",
          item_id: item.id,
          placement: "featured_vault_item",
        });
      } else if (mode === "edit" && itemId && !values.feature_on_legacy) {
        if (initial.feature_on_legacy) {
          await clearLegacyFeaturedPlacement("featured_vault_item");
        }
      }
      setNote(mode === "create" ? "Drop created" : "Vault drop saved");
      onSaved?.(item);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="max-w-3xl">
      {error ? (
        <Alert tone="danger" title="Could not save" className="mb-6">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Saved" className="mb-6">
          {note}
        </Alert>
      ) : null}

      <form className="space-y-8" onSubmit={handleSubmit}>
        <FormSection
          title="Drop identity"
          description="Exclusive host content — fans unlock by follow, ticket, attendance, VIP, or purchase."
        >
          <Input
            label="Title"
            value={values.title}
            onChange={(e) => setValues({ ...values, title: e.target.value })}
            required
          />
          {mode === "edit" ? (
            <Input
              label="Slug"
              value={values.slug}
              onChange={(e) => setValues({ ...values, slug: e.target.value })}
              hint="Public path: /@{username}/vault/{slug}"
            />
          ) : null}
          <Select
            label="Content type"
            value={values.content_type}
            onChange={(e) => setValues({ ...values, content_type: e.target.value })}
            hint={CONTENT_TYPE_HINTS[values.content_type]}
          >
            {CONTENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {formatLabel(t)}
              </option>
            ))}
          </Select>
          <Textarea
            label="Description"
            value={values.description}
            onChange={(e) => setValues({ ...values, description: e.target.value })}
            hint="Public description of the drop (safe to show when locked)."
            className="min-h-[72px]"
          />
          <ImageUrlOrUploadField
            label="Cover image"
            hint="Hero image shown on catalog cards."
            value={values.cover_url}
            onChange={(url) => setValues({ ...values, cover_url: url })}
            mediaType="other"
            previewClassName="h-16 w-24"
          />
          <Input
            label="Tags"
            value={values.tags}
            onChange={(e) => setValues({ ...values, tags: e.target.value })}
            hint="Comma-separated, e.g. vip, recap, afrobeats"
            placeholder="vip, recap"
          />
        </FormSection>

        <FormSection
          title="Access & monetization"
          description="Server-side access rules — never trust the client."
        >
          <VaultAccessRuleEditor
            value={values.access}
            onChange={(access) => setValues({ ...values, access })}
            events={events}
          />
        </FormSection>

        <FormSection
          title="Content"
          description="Preview/teaser is public. Body, file URL, and external URL stay locked until entitlement."
        >
          <Textarea
            label="Teaser / preview text"
            value={values.preview_text}
            onChange={(e) => setValues({ ...values, preview_text: e.target.value })}
            hint="Short teaser on Legacy and locked Vault pages."
            className="min-h-[80px]"
          />
          <Textarea
            label="Content body"
            value={values.body}
            onChange={(e) => setValues({ ...values, body: e.target.value })}
            hint="Full exclusive text — never returned without access."
          />
          {needsFile || values.file_url ? (
            <Input
              label="File URL"
              value={values.file_url}
              onChange={(e) => setValues({ ...values, file_url: e.target.value })}
              placeholder="https://"
              hint="Primary download for file_download / discount assets. Locked without access."
              required={values.content_type === "file_download"}
            />
          ) : null}
          {needsExternal || values.external_url ? (
            <Input
              label="External URL"
              value={values.external_url}
              onChange={(e) => setValues({ ...values, external_url: e.target.value })}
              placeholder="https://"
              hint="Revealed after unlock for external_link drops."
              required={needsExternal}
            />
          ) : (
            <Input
              label="External URL (optional)"
              value={values.external_url}
              onChange={(e) => setValues({ ...values, external_url: e.target.value })}
              placeholder="https://"
              hint="Optional private link revealed after unlock."
            />
          )}
        </FormSection>

        <FormSection title="Media URLs" description="Mark teaser assets as public preview.">
          <VaultMediaEditor
            value={values.media}
            onChange={(media) => setValues({ ...values, media })}
          />
        </FormSection>

        <FormSection
          title="Related context"
          description="Optional links to an event or Event Memory on your Legacy."
        >
          <Select
            label="Related event"
            value={values.related_event_id}
            onChange={(e) =>
              setValues({
                ...values,
                related_event_id: e.target.value,
                related_memory_id: "",
              })
            }
          >
            <option value="">None</option>
            {events.map((event) => (
              <option key={event.id} value={event.id}>
                {event.title}
              </option>
            ))}
          </Select>
          <Select
            label="Related memory"
            value={values.related_memory_id}
            onChange={(e) =>
              setValues({ ...values, related_memory_id: e.target.value })
            }
            hint={
              memoriesForSelect.length === 0
                ? "No Event Memories found for the selected event yet."
                : "Must belong to the related event when both are set."
            }
          >
            <option value="">None</option>
            {memoriesForSelect.map((memory) => (
              <option key={memory.id} value={memory.id}>
                {memory.label}
              </option>
            ))}
          </Select>
        </FormSection>

        <FormSection title="Publish & Legacy">
          <Select
            label="Status"
            value={values.status}
            onChange={(e) => setValues({ ...values, status: e.target.value })}
          >
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="scheduled">Scheduled</option>
            {mode === "edit" ? (
              <option value="archived">Archived</option>
            ) : null}
          </Select>
          <Input
            label="Expiry date (optional)"
            type="datetime-local"
            value={values.expires_at}
            onChange={(e) => setValues({ ...values, expires_at: e.target.value })}
            hint="After this time the drop leaves the public catalog and unlocks stop."
          />
          {mode === "edit" && initial && values.status === "published" ? (
            <p className="text-xs text-muted-foreground">
              Publish date is set server-side when the drop first goes live.
            </p>
          ) : null}
          <label className="flex items-start gap-3 rounded-[var(--radius-md)] border border-border bg-muted/50 px-4 py-3 text-sm">
            <input
              type="checkbox"
              className="mt-0.5 accent-accent"
              checked={values.feature_on_legacy}
              onChange={(e) =>
                setValues({ ...values, feature_on_legacy: e.target.checked })
              }
            />
            <span>
              <span className="font-semibold text-foreground">
                Feature on Legacy Vault preview
              </span>
              <span className="mt-0.5 block text-muted-foreground">
                Pins this drop as the featured Vault item on your public Legacy Page.
              </span>
            </span>
          </label>
        </FormSection>

        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={busy} size="lg">
            {busy ? "Saving…" : submitLabel}
          </Button>
          {secondaryActions}
        </div>
      </form>
    </Card>
  );
}
