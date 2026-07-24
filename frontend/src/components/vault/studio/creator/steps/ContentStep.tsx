"use client";

import type { VaultItemEditorValues } from "@/components/vault/studio/VaultItemEditor";
import { Input, Select, Textarea } from "@/components/ui";
import { CONTENT_TYPE_HINTS, CONTENT_TYPES } from "@/lib/types/vault";

import { slugifyTitle } from "../types";

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

type Props = {
  values: VaultItemEditorValues;
  onChange: (next: VaultItemEditorValues) => void;
};

export function ContentStep({ values, onChange }: Props) {
  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <h2 className="text-xl font-extrabold text-foreground">Content</h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Define the exclusive drop. Teasers stay public; the body stays locked
          until fans unlock access.
        </p>
      </div>

      <Input
        label="Title"
        value={values.title}
        onChange={(e) => {
          const title = e.target.value;
          const nextSlug =
            !values.slug.trim() || values.slug === slugifyTitle(values.title)
              ? slugifyTitle(title)
              : values.slug;
          onChange({ ...values, title, slug: nextSlug });
        }}
        required
        placeholder="VIP afterparty gallery"
      />

      <Input
        label="Slug"
        value={values.slug}
        onChange={(e) => onChange({ ...values, slug: e.target.value })}
        hint="Public path: /@{username}/vault/{slug}"
        placeholder="vip-afterparty-gallery"
      />

      <Select
        label="Content type"
        value={values.content_type}
        onChange={(e) => onChange({ ...values, content_type: e.target.value })}
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
        onChange={(e) => onChange({ ...values, description: e.target.value })}
        hint="Public description safe to show when locked."
        className="min-h-[80px]"
      />

      <Textarea
        label="Teaser"
        value={values.preview_text}
        onChange={(e) => onChange({ ...values, preview_text: e.target.value })}
        hint="Short teaser on Legacy and locked Vault pages."
        className="min-h-[72px]"
        placeholder="A private look at last night’s VIP set…"
      />

      <Textarea
        label="Body / content"
        value={values.body}
        onChange={(e) => onChange({ ...values, body: e.target.value })}
        hint="Full exclusive text — never returned without access."
        className="min-h-[160px]"
      />

      <Input
        label="Tags"
        value={values.tags}
        onChange={(e) => onChange({ ...values, tags: e.target.value })}
        hint="Comma-separated, e.g. vip, recap, afrobeats"
        placeholder="vip, recap"
      />
    </div>
  );
}
