"use client";

import { useCallback, useState } from "react";

import { Alert, Button } from "@/components/ui";
import {
  generateAdminAI,
  recordAdminAIGenerationFeedback,
} from "@/lib/ai-api";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { BlogTag } from "@/lib/blog-api";
import type { AISuggestion } from "@/lib/types/ai";

const FEATURE_TITLE = "admin.blog.title";
const FEATURE_OUTLINE = "admin.blog.outline";
const FEATURE_EXCERPT = "admin.blog.excerpt";
const FEATURE_SEO = "admin.blog.seo_meta";
const FEATURE_TAGS = "admin.blog.tags";
const FEATURE_SOCIAL = "admin.blog.social_snippets";

const UNAVAILABLE =
  "AI is unavailable right now. You can keep editing manually.";

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const detail = err.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return UNAVAILABLE;
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    /* ignore */
  }
}

type PanelKey =
  | "title"
  | "outline"
  | "excerpt"
  | "seo"
  | "tags"
  | "social"
  | null;

export type BlogAIDraftValues = {
  title: string;
  excerpt: string;
  body: string;
  categoryName?: string;
  existingTags?: string;
  existingSlug?: string;
  existingSeoTitle?: string;
  existingSeoDescription?: string;
  audience?: string;
  goal?: string;
};

export function BlogAIAssist({
  blogPostId,
  values,
  catalogTags,
  onApplyTitle,
  onApplyOutline,
  onApplyExcerpt,
  onApplySeo,
  onApplyTags,
}: {
  blogPostId?: string | null;
  values: BlogAIDraftValues;
  catalogTags: BlogTag[];
  onApplyTitle: (title: string) => void;
  onApplyOutline: (outline: string) => void;
  onApplyExcerpt: (excerpt: string) => void;
  onApplySeo: (meta: {
    seo_title: string;
    seo_description: string;
    suggested_slug: string;
    og_description?: string;
  }) => void;
  onApplyTags: (tagIds: string[]) => void;
}) {
  const [busy, setBusy] = useState<PanelKey>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<PanelKey>(null);
  const [result, setResult] = useState<AISuggestion | null>(null);

  const extra = useCallback((): Record<string, string> => {
    return {
      title: values.title || "",
      excerpt: values.excerpt || "",
      body: values.body || "",
      category: values.categoryName || "",
      existing_tags: values.existingTags || "",
      existing_slug: values.existingSlug || "",
      existing_seo_title: values.existingSeoTitle || "",
      existing_seo_description: values.existingSeoDescription || "",
      audience: values.audience || "",
      goal: values.goal || "",
    };
  }, [values]);

  const run = useCallback(
    async (feature: string, panel: Exclude<PanelKey, null>) => {
      setBusy(panel);
      setError(null);
      setActive(panel);
      try {
        const data = await generateAdminAI({
          feature,
          blog_post_id: blogPostId || undefined,
          extra: extra(),
        });
        setResult(data);
      } catch (err) {
        setResult(null);
        setError(errorMessage(err));
      } finally {
        setBusy(null);
      }
    },
    [blogPostId, extra],
  );

  const feedback = useCallback(
    async (
      action: "applied" | "dismissed",
      appliedField?: string,
      selected?: string,
    ) => {
      if (!result?.usage_log_id) return;
      try {
        await recordAdminAIGenerationFeedback({
          usage_log_id: result.usage_log_id,
          action,
          blog_post_id: blogPostId || undefined,
          applied_field: appliedField,
          selected_option: selected,
        });
      } catch {
        /* non-blocking */
      }
    },
    [blogPostId, result?.usage_log_id],
  );

  const dismiss = useCallback(async () => {
    await feedback("dismissed");
    setResult(null);
    setActive(null);
    setError(null);
  }, [feedback]);

  function resolveTagIds(names: string[]): string[] {
    const ids: string[] = [];
    for (const name of names) {
      const hit = catalogTags.find(
        (t) =>
          t.name.toLowerCase() === name.toLowerCase() ||
          t.slug.toLowerCase() === name.toLowerCase(),
      );
      if (hit) ids.push(hit.id);
    }
    return ids;
  }

  return (
    <div
      className={cn(
        "space-y-3 rounded-[var(--radius-md)] border border-border",
        "bg-surface px-4 py-4",
      )}
    >
      <div className="space-y-1">
        <p className="text-sm font-semibold text-foreground">
          AI writing assistant
        </p>
        <p className="text-xs text-muted-foreground">
          AI suggestions are drafts. Review before publishing.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="secondary"
          disabled={busy !== null}
          onClick={() => void run(FEATURE_TITLE, "title")}
        >
          {busy === "title" ? "Generating…" : "Generate title ideas"}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={busy !== null}
          onClick={() => void run(FEATURE_OUTLINE, "outline")}
        >
          {busy === "outline" ? "Generating…" : "Generate outline"}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={busy !== null}
          onClick={() => void run(FEATURE_EXCERPT, "excerpt")}
        >
          {busy === "excerpt" ? "Generating…" : "Generate excerpt"}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={busy !== null}
          onClick={() => void run(FEATURE_SEO, "seo")}
        >
          {busy === "seo" ? "Generating…" : "Generate SEO meta"}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={busy !== null}
          onClick={() => void run(FEATURE_TAGS, "tags")}
        >
          {busy === "tags" ? "Suggesting…" : "Suggest tags"}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={busy !== null}
          onClick={() => void run(FEATURE_SOCIAL, "social")}
        >
          {busy === "social" ? "Generating…" : "Generate social snippets"}
        </Button>
      </div>

      {error ? (
        <Alert tone="danger" title="AI writing assistant">
          {error}
        </Alert>
      ) : null}

      {result && active ? (
        <div className="space-y-3 rounded-[var(--radius-md)] border border-border bg-surface-inset px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {result.label}
          </p>

          {active === "title" && result.options?.length ? (
            <ul className="space-y-2">
              {result.options.map((opt) => (
                <li key={opt}>
                  <button
                    type="button"
                    className="w-full rounded-[var(--radius-sm)] border border-border bg-surface px-3 py-2 text-left text-sm font-medium text-foreground hover:border-primary"
                    onClick={() =>
                      void (async () => {
                        onApplyTitle(opt);
                        await feedback("applied", "title", opt);
                        setResult(null);
                        setActive(null);
                      })()
                    }
                  >
                    {opt}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <pre className="whitespace-pre-wrap font-sans text-sm text-foreground">
              {result.suggestion}
            </pre>
          )}

          <div className="flex flex-wrap gap-2">
            {active === "outline" ? (
              <Button
                size="sm"
                onClick={() =>
                  void (async () => {
                    onApplyOutline(result.suggestion);
                    await feedback("applied", "body_outline");
                    setResult(null);
                    setActive(null);
                  })()
                }
              >
                Apply to editor
              </Button>
            ) : null}
            {active === "excerpt" ? (
              <Button
                size="sm"
                onClick={() =>
                  void (async () => {
                    onApplyExcerpt(result.suggestion);
                    await feedback("applied", "excerpt");
                    setResult(null);
                    setActive(null);
                  })()
                }
              >
                Apply excerpt
              </Button>
            ) : null}
            {active === "seo" &&
            result.seo_title &&
            result.seo_description &&
            result.suggested_slug ? (
              <Button
                size="sm"
                onClick={() =>
                  void (async () => {
                    onApplySeo({
                      seo_title: result.seo_title!,
                      seo_description: result.seo_description!,
                      suggested_slug: result.suggested_slug!,
                      og_description: result.og_description || undefined,
                    });
                    await feedback("applied", "seo_meta");
                    setResult(null);
                    setActive(null);
                  })()
                }
              >
                Apply SEO fields
              </Button>
            ) : null}
            {active === "tags" && result.tags?.length ? (
              <Button
                size="sm"
                onClick={() =>
                  void (async () => {
                    const ids = resolveTagIds(result.tags || []);
                    if (ids.length) onApplyTags(ids);
                    await feedback("applied", "tags");
                    setResult(null);
                    setActive(null);
                  })()
                }
              >
                Apply tags
              </Button>
            ) : null}
            <Button
              size="sm"
              variant="secondary"
              onClick={() => void copyText(result.suggestion)}
            >
              Copy
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={busy !== null}
              onClick={() => {
                const map: Record<Exclude<PanelKey, null>, string> = {
                  title: FEATURE_TITLE,
                  outline: FEATURE_OUTLINE,
                  excerpt: FEATURE_EXCERPT,
                  seo: FEATURE_SEO,
                  tags: FEATURE_TAGS,
                  social: FEATURE_SOCIAL,
                };
                if (active) void run(map[active], active);
              }}
            >
              Regenerate
            </Button>
            <Button size="sm" variant="ghost" onClick={() => void dismiss()}>
              Dismiss
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
