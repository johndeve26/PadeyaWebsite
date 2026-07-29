"use client";

import { Input, Textarea } from "@/components/ui";
import { ImageUrlOrUploadField } from "@/components/media/ImageUrlOrUploadField";
import type { BlogBlock, ContentWidth, SpacingPreset } from "@/lib/blog-document";

type Props = {
  block: BlogBlock | null;
  onChange: (blockId: string, patch: Partial<BlogBlock>) => void;
};

export function BlogBlockSettings({ block, onChange }: Props) {
  if (!block) {
    return (
      <p className="text-sm text-muted p-4">Select a block to edit its settings.</p>
    );
  }

  const updateProps = (key: string, value: unknown) => {
    onChange(block.id, {
      props: { ...block.props, [key]: value },
    });
  };

  const updateContent = (key: string, value: unknown) => {
    onChange(block.id, {
      content: { ...block.content, [key]: value },
    });
  };

  return (
    <div className="space-y-4 p-4 text-sm">
      <p className="font-medium capitalize">{block.type.replace(/_/g, " ")}</p>

      <label className="block space-y-1">
        <span className="text-muted">Content width</span>
        <select
          className="w-full rounded-[var(--radius-md)] border border-border bg-surface px-2 py-1.5"
          value={String(block.props.content_width || "standard")}
          onChange={(e) => updateProps("content_width", e.target.value as ContentWidth)}
        >
          <option value="narrow">Narrow</option>
          <option value="standard">Standard</option>
          <option value="wide">Wide</option>
          <option value="full">Full width</option>
        </select>
      </label>

      <label className="block space-y-1">
        <span className="text-muted">Spacing</span>
        <select
          className="w-full rounded-[var(--radius-md)] border border-border bg-surface px-2 py-1.5"
          value={String(block.props.spacing || "normal")}
          onChange={(e) => updateProps("spacing", e.target.value as SpacingPreset)}
        >
          <option value="none">None</option>
          <option value="compact">Compact</option>
          <option value="normal">Normal</option>
          <option value="spacious">Spacious</option>
        </select>
      </label>

      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={Boolean(block.props.include_in_toc ?? true)}
          onChange={(e) => updateProps("include_in_toc", e.target.checked)}
        />
        <span>Include in table of contents</span>
      </label>

      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={Boolean(block.props.locked)}
          onChange={(e) => updateProps("locked", e.target.checked)}
        />
        <span>Lock block</span>
      </label>

      {block.type === "heading" ? (
        <label className="block space-y-1">
          <span className="text-muted">Heading text</span>
          <Input
            value={String(block.content.text || "")}
            onChange={(e) => updateContent("text", e.target.value)}
          />
        </label>
      ) : null}

      {block.type === "image" ? (
        <>
          <ImageUrlOrUploadField
            label="Image"
            hint="Upload JPEG, PNG, WebP, or GIF. SVG is not accepted."
            value={String(block.content.url || "")}
            onChange={(url) => updateContent("url", url)}
            mediaType="blog"
            disabled={Boolean(block.props.locked)}
            onUploaded={(url) => updateContent("url", url)}
          />
          <label className="block space-y-1">
            <span className="text-muted">Alt text</span>
            <Input
              value={String(block.content.alt || "")}
              onChange={(e) => updateContent("alt", e.target.value)}
            />
          </label>
          {!block.content.alt ? (
            <p className="text-amber-600 text-xs">Missing alt text — add for accessibility.</p>
          ) : null}
          <label className="block space-y-1">
            <span className="text-muted">Caption</span>
            <Input
              value={String(block.content.caption || "")}
              onChange={(e) => updateContent("caption", e.target.value)}
            />
          </label>
          <p className="text-xs text-muted">
            Removing this block does not delete the stored file (v1 policy).
          </p>
        </>
      ) : null}

      {block.type === "cta" ? (
        <>
          <label className="block space-y-1">
            <span className="text-muted">Label</span>
            <Input
              value={String(block.content.label || "")}
              onChange={(e) => updateContent("label", e.target.value)}
            />
          </label>
          <label className="block space-y-1">
            <span className="text-muted">Link</span>
            <Input
              value={String(block.content.href || "")}
              onChange={(e) => updateContent("href", e.target.value)}
            />
          </label>
        </>
      ) : null}

      {(block.type === "rich_text" || block.type === "legacy_rich_text") ? (
        <label className="block space-y-1">
          <span className="text-muted">Markdown</span>
          <Textarea
            rows={8}
            value={String(block.content.markdown || "")}
            onChange={(e) => updateContent("markdown", e.target.value)}
          />
        </label>
      ) : null}
    </div>
  );
}
