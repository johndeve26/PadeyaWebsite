"use client";

import Link from "next/link";

import {
  Badge,
  Button,
  ConfirmAction,
  Input,
  Select,
  Switch,
  Textarea,
} from "@/components/ui";
import type { BlogAuthor, BlogCategory, BlogTag } from "@/lib/blog-api";

import type { AutosaveStatus } from "./types";
import { StudioPanel } from "./BlogStudioShell";

function autosaveLabel(status: AutosaveStatus) {
  if (status === "saving") return "Saving…";
  if (status === "saved") return "Saved";
  if (status === "failed") return "Save failed";
  if (status === "conflict") return "Version conflict — reload or save again";
  return null;
}

export function BlogPublishPanel({
  status,
  featured,
  scheduledAt,
  categoryId,
  authorId,
  tagIds,
  categories,
  authors,
  tags,
  adminNotes,
  autosaveStatus,
  busy,
  previewOpen,
  postId,
  slug,
  onChange,
  onToggleTag,
  onSaveDraft,
  onTogglePreview,
  onPublish,
  onUnpublish,
  onArchive,
}: {
  status: string;
  featured: boolean;
  scheduledAt: string;
  categoryId: string;
  authorId: string;
  tagIds: string[];
  categories: BlogCategory[];
  authors: BlogAuthor[];
  tags: BlogTag[];
  adminNotes: string;
  autosaveStatus: AutosaveStatus;
  busy?: boolean;
  previewOpen: boolean;
  postId: string | null;
  slug: string;
  onChange: (patch: Record<string, string | boolean>) => void;
  onToggleTag: (tagId: string) => void;
  onSaveDraft: () => void;
  onTogglePreview: () => void;
  onPublish: () => void;
  onUnpublish: () => void;
  onArchive: () => void;
}) {
  const saveHint = autosaveLabel(autosaveStatus);

  return (
    <StudioPanel title="Publishing" description="AI never auto-publishes.">
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-muted-foreground">Status</span>
          <Badge tone={status === "published" ? "success" : "neutral"}>
            {status}
          </Badge>
        </div>
        {saveHint ? (
          <p className="text-xs font-semibold text-foreground">{saveHint}</p>
        ) : null}
        <Select
          label="Category"
          value={categoryId}
          onChange={(e) => onChange({ categoryId: e.target.value })}
        >
          <option value="">None</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <Select
          label="Author"
          value={authorId}
          onChange={(e) => onChange({ authorId: e.target.value })}
        >
          <option value="">None</option>
          {authors.map((a) => (
            <option key={a.id} value={a.id}>
              {a.display_name}
            </option>
          ))}
        </Select>
        <div>
          <p className="mb-2 text-sm font-semibold">Tags</p>
          <div className="flex flex-wrap gap-2">
            {tags.map((t) => {
              const on = tagIds.includes(t.id);
              return (
                <button
                  key={t.id}
                  type="button"
                  className={
                    on
                      ? "rounded-full bg-primary px-3 py-1 text-xs font-bold text-primary-foreground"
                      : "rounded-full border border-border px-3 py-1 text-xs font-semibold"
                  }
                  onClick={() => onToggleTag(t.id)}
                >
                  {t.name}
                </button>
              );
            })}
          </div>
        </div>
        <Input
          label="Schedule publish"
          type="datetime-local"
          value={scheduledAt}
          onChange={(e) => onChange({ scheduledAt: e.target.value })}
        />
        <Switch
          checked={featured}
          onCheckedChange={(v) => onChange({ featured: v })}
          label="Featured on blog home"
        />
        <Textarea
          label="Admin notes (private)"
          rows={2}
          value={adminNotes}
          onChange={(e) => onChange({ adminNotes: e.target.value })}
          hint="Never shown on the public blog."
        />
        <div className="flex flex-wrap gap-2 pt-1">
          <Button disabled={busy} variant="secondary" onClick={onSaveDraft}>
            Save draft
          </Button>
          <Button disabled={busy} variant="ghost" onClick={onTogglePreview}>
            {previewOpen ? "Hide preview" : "Preview"}
          </Button>
          {status !== "published" ? (
            <ConfirmAction
              label="Publish"
              title="Publish this post?"
              description="This will make the article publicly indexable. AI never publishes automatically — confirm to continue."
              confirmLabel="Publish now"
              disabled={busy}
              busy={busy}
              onConfirm={onPublish}
            />
          ) : (
            <Button disabled={busy} variant="secondary" onClick={onUnpublish}>
              Unpublish
            </Button>
          )}
          {postId ? (
            <ConfirmAction
              label="Archive"
              title="Archive this post?"
              description="The post will be removed from the public blog. You can restore later from admin if supported."
              confirmLabel="Archive"
              tone="danger"
              disabled={busy}
              busy={busy}
              onConfirm={onArchive}
            />
          ) : null}
        </div>
        {status === "published" && slug ? (
          <Link
            href={`/blog/${slug}`}
            target="_blank"
            className="inline-block text-sm font-semibold text-primary"
          >
            Open public /blog/{slug}
          </Link>
        ) : (
          <p className="text-[11px] text-muted-foreground">
            Public link available only after publish. Drafts are not indexable.
          </p>
        )}
      </div>
    </StudioPanel>
  );
}
