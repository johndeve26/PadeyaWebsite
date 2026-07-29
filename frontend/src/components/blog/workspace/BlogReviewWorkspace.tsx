"use client";
// BlogReviewWorkspace — Review tab: checklist + AI tools + version history

import { useState } from "react";
import { Button } from "@/components/ui";
import { useBlogStudio } from "@/components/blog/studio/BlogStudioProvider";
import {
  BlogQualityReviewPanel,
} from "@/components/blog/studio/BlogQualityReviewPanel";
import {
  BlogFactReviewPanel,
} from "@/components/blog/studio/BlogFactReviewPanel";
import {
  BlogInternalLinksPanel,
} from "@/components/blog/studio/BlogInternalLinksPanel";
import {
  BlogVersionHistory,
} from "@/components/blog/studio/BlogVersionHistory";
import { BlogFaqEditor } from "@/components/blog/studio/BlogFaqEditor";
import { computeChecklist } from "@/lib/blog-workspace";
import type { WorkspaceTab } from "@/lib/blog-workspace";
import { cn } from "@/lib/cn";
import {
  studioReviewArticle,
  studioFactReview,
  studioSuggestInternalLinks,
  studioGenerateFaqs,
  studioListRevisions,
  studioRestoreRevision,
  studioCheckpointRevision,
} from "@/lib/blog-studio-api";
import {
  normalizeFactClaims,
  normalizeInternalLinks,
  normalizeFaqs,
} from "@/lib/blog-studio-api";
import type { BlogRevisionPublic, BlogInternalLinkSuggestion } from "@/components/blog/studio/types";
import { newFaqId } from "@/components/blog/studio/types";
import { ApiError } from "@/lib/api";
import { useToast } from "@/components/ui";
import { useBlogStudioAutosave } from "@/components/blog/studio/useBlogStudioAutosave";

type Props = {
  onNavigate: (tab: WorkspaceTab) => void;
};

function ChecklistRow({
  ok,
  label,
  fixTab,
  onFix,
}: {
  ok: boolean;
  label: string;
  fixTab?: WorkspaceTab;
  onFix?: (tab: WorkspaceTab) => void;
}) {
  return (
    <li className="flex items-center justify-between py-1.5 gap-3">
      <div className="flex items-center gap-2 min-w-0">
        <span
          className={cn(
            "shrink-0 h-4 w-4 rounded-full flex items-center justify-center text-white text-xs",
            ok ? "bg-success" : "bg-amber-400",
          )}
        >
          {ok ? "✓" : "!"}
        </span>
        <span className="text-sm truncate">{label}</span>
      </div>
      {!ok && fixTab && onFix ? (
        <button
          type="button"
          className="shrink-0 text-xs text-primary hover:underline"
          onClick={() => onFix(fixTab)}
        >
          Fix →
        </button>
      ) : null}
    </li>
  );
}

export function BlogReviewWorkspace({ onNavigate }: Props) {
  const studio = useBlogStudio();
  const toast = useToast();
  const { saveNow } = useBlogStudioAutosave({ enabled: true });
  const [revisions, setRevisions] = useState<BlogRevisionPublic[]>([]);
  const [busyAction, setBusyAction] = useState(false);

  const checklist = computeChecklist(
    {
      title: studio.title,
      slug: studio.slug,
      seoTitle: studio.seoTitle,
      seoDescription: studio.seoDescription,
      focusKeyword: studio.focusKeyword,
    },
    { blocks: (studio.contentDocument?.blocks ?? []) as Array<{ type?: string; props?: Record<string, unknown> }> },
  );

  async function runAi<T>(
    stage: Parameters<typeof studio.beginGeneration>[0],
    message: string,
    fn: () => Promise<T>,
  ): Promise<T | null> {
    if (studio.generating) return null;
    studio.beginGeneration(stage, message);
    try {
      const result = await fn();
      if (studio.isCancelled()) return null;
      return result;
    } catch (e) {
      toast.push({ tone: "danger", title: e instanceof ApiError ? e.message : "AI request failed" });
      return null;
    } finally {
      studio.endGeneration();
    }
  }

  const studioBase = () => ({
    brief: studio.brief,
    outline: studio.outline,
    blog_post_id: studio.postId,
    title: studio.title,
    excerpt: studio.excerpt,
    body: studio.body,
    slug: studio.slug,
    focus_keyword: studio.focusKeyword || studio.brief.primary_keyword,
    secondary_keywords:
      studio.secondaryKeywords.length > 0
        ? studio.secondaryKeywords
        : studio.brief.secondary_keywords,
    locked_section_ids: [],
    client_request_id: crypto.randomUUID?.() ?? `req-${Date.now()}`,
  });

  const refreshRevisions = async () => {
    if (!studio.postId) return;
    try {
      const list = await studioListRevisions(studio.postId);
      setRevisions(list);
    } catch {
      /* endpoint may not exist yet */
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Checklist */}
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Content checklist
          </h2>
          <ul className="divide-y divide-border rounded-lg border border-border bg-card px-4">
            {checklist.map((item) => (
              <ChecklistRow
                key={item.id}
                ok={item.ok}
                label={item.label}
                fixTab={item.fixTab}
                onFix={onNavigate}
              />
            ))}
          </ul>
        </section>

        {/* AI review tools */}
        <section className="space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            AI review tools
          </h2>
          <BlogQualityReviewPanel
            review={studio.qualityReview}
            busy={studio.generating}
            onRun={() =>
              void (async () => {
                const res = await runAi("review", "Reviewing article…", () =>
                  studioReviewArticle(studioBase()),
                );
                if (res) studio.patch({ qualityReview: res });
              })()
            }
          />
          <BlogFactReviewPanel
            claims={studio.factClaims}
            busy={studio.generating}
            onRun={() =>
              void (async () => {
                const res = await runAi("facts", "Reviewing claims…", () =>
                  studioFactReview(studioBase()),
                );
                if (res) studio.patch({ factClaims: normalizeFactClaims(res) });
              })()
            }
          />
          <BlogInternalLinksPanel
            suggestions={studio.internalLinks}
            busy={studio.generating}
            onRun={() =>
              void (async () => {
                const res = await runAi("links", "Finding links…", () =>
                  studioSuggestInternalLinks(studioBase()),
                );
                if (res) studio.patch({ internalLinks: normalizeInternalLinks(res) });
              })()
            }
            onInsert={(s: BlogInternalLinkSuggestion) => {
              const anchor = s.suggested_anchor || s.target_title || "Learn more";
              studio.setBody((prev) => `${prev.trim()}\n\n[${anchor}](${s.target_url})\n`);
            }}
            onDismiss={(s: BlogInternalLinkSuggestion) => {
              studio.patch({
                internalLinks: studio.internalLinks.map((x) =>
                  x.target_url === s.target_url && x.suggested_anchor === s.suggested_anchor
                    ? { ...x, dismissed: true }
                    : x,
                ),
              });
            }}
          />
          <BlogFaqEditor
            faqs={studio.faqs}
            busy={studio.generating}
            onChange={(faqs) => studio.setFaqs(faqs)}
            onGenerate={() =>
              void (async () => {
                const res = await runAi("faqs", "Generating FAQs…", () =>
                  studioGenerateFaqs(studioBase()),
                );
                if (!res) return;
                const faqs = normalizeFaqs(res).map((f) => ({ ...f, id: f.id || newFaqId() }));
                studio.setFaqs(faqs);
              })()
            }
          />
        </section>

        {/* Version history */}
        {studio.postId ? (
          <section className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Version history
            </h2>
            <BlogVersionHistory
              revisions={revisions}
              busy={busyAction || studio.generating}
              onRefresh={() => void refreshRevisions()}
              onPreview={(r) => {
                window.alert(`Revision ${r.id}\n${r.summary || r.action_type || ""}`);
              }}
              onRestore={(r) =>
                void (async () => {
                  setBusyAction(true);
                  try {
                    await studioRestoreRevision(studio.postId!, r.id);
                    toast.push({ tone: "success", title: "Revision restored" });
                    await refreshRevisions();
                  } catch (e) {
                    toast.push({ tone: "danger", title: e instanceof ApiError ? e.message : "Restore failed" });
                  } finally {
                    setBusyAction(false);
                  }
                })()
              }
              onCheckpoint={() =>
                void (async () => {
                  if (!studio.postId) return;
                  setBusyAction(true);
                  try {
                    await saveNow();
                    await studioCheckpointRevision(studio.postId, { summary: "Manual checkpoint" });
                    await refreshRevisions();
                    toast.push({ tone: "success", title: "Checkpoint saved" });
                  } catch (e) {
                    toast.push({ tone: "danger", title: e instanceof ApiError ? e.message : "Checkpoint failed" });
                  } finally {
                    setBusyAction(false);
                  }
                })()
              }
            />
          </section>
        ) : null}

        <div className="pt-4 border-t border-border">
          <Button onClick={() => onNavigate("publish")} className="gap-2">
            Continue to Publish →
          </Button>
        </div>
      </div>
    </div>
  );
}
