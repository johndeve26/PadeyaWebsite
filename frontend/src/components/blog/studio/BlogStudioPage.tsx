"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { BlogEditorShell } from "@/components/blog/editor";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  isBlockDocumentMode,
  parseContentDocument,
  resolveContentMode,
} from "@/lib/blog-document";
import { Alert, Badge, Button, Input, Textarea, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  checkBlogSlug,
  deleteAdminBlogPost,
  fetchAdminBlogAuthors,
  fetchAdminBlogCategories,
  fetchAdminBlogTags,
  publishAdminBlogPost,
  unpublishAdminBlogPost,
  type BlogAuthor,
  type BlogCategory,
  type BlogPost,
  type BlogTag,
} from "@/lib/blog-api";
import {
  normalizeFactClaims,
  normalizeFaqs,
  normalizeInternalLinks,
  normalizeTitleSuggestions,
  studioCheckpointRevision,
  studioFactReview,
  studioGenerateFaqs,
  studioGenerateFullDraft,
  studioGenerateImagePrompt,
  studioGenerateOutline,
  studioGenerateSection,
  studioGenerateSeoBrief,
  studioGenerateTitles,
  studioGetRevision,
  studioListRevisions,
  studioPreviewPost,
  studioRegenerateOutlineSection,
  studioRestoreRevision,
  studioReviewArticle,
  studioRewriteSelection,
  studioSeoScore,
  studioSuggestInternalLinks,
} from "@/lib/blog-studio-api";

import { AiGenerationProgress } from "./AiGenerationProgress";
import { AiSuggestionDiff } from "./AiSuggestionDiff";
import { BlogAiWorkflow } from "./BlogAiWorkflow";
import { BlogContentBriefPanel } from "./BlogContentBriefPanel";
import { BlogFactReviewPanel } from "./BlogFactReviewPanel";
import { BlogFaqEditor } from "./BlogFaqEditor";
import { BlogImageAssistant } from "./BlogImageAssistant";
import { BlogInlineAiMenu } from "./BlogInlineAiMenu";
import { BlogInternalLinksPanel } from "./BlogInternalLinksPanel";
import { BlogOutlineEditor } from "./BlogOutlineEditor";
import { BlogPublishPanel } from "./BlogPublishPanel";
import { BlogPostAnalyticsPanel } from "./BlogPostAnalyticsPanel";
import { BlogQualityReviewPanel } from "./BlogQualityReviewPanel";
import { BlogSectionToolbar } from "./BlogSectionToolbar";
import {
  BlogSeoScoreStatus,
  BlogSettingsSummary,
} from "./BlogSettingsSummary";
import { BlogSeoPanel } from "./BlogSeoPanel";
import { BlogStudioProvider, useBlogStudio } from "./BlogStudioProvider";
import { BlogStudioShell } from "./BlogStudioShell";
import { BlogVersionHistory } from "./BlogVersionHistory";
import {
  deleteSection,
  duplicateSection,
  insertSectionBelow,
  moveSection,
  outlineToMarkdown,
  parseMarkdownH2Sections,
  replaceSectionAt,
  simpleMarkdownToHtml,
} from "./markdown-utils";
import type {
  BlogContentBrief,
  BlogFaqItem,
  BlogInternalLinkSuggestion,
  BlogOutline,
  BlogRevisionPublic,
  BlogWorkflowStepId,
  RewriteAction,
} from "./types";
import { newClientRequestId, newFaqId, newSectionId } from "./types";
import {
  clearLocalStudioDraft,
  readLocalStudioDraft,
  useBlogStudioAutosave,
} from "./useBlogStudioAutosave";

function studioBase(studio: ReturnType<typeof useBlogStudio>) {
  return {
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
    locked_section_ids: studio.outline.sections
      .filter((s) => s.locked)
      .map((s) => s.id),
    client_request_id: newClientRequestId(),
  };
}

function confirmOverwrite(fieldLabel: string, current: string): boolean {
  if (!current.trim()) return true;
  return window.confirm(
    `Replace the current ${fieldLabel} with the AI suggestion?`,
  );
}

function BlogStudioInner({
  mode,
  initialPost,
}: {
  mode: "new" | "edit";
  initialPost?: BlogPost | null;
}) {
  const studio = useBlogStudio();
  const toast = useToast();
  const router = useRouter();
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);
  const [categories, setCategories] = useState<BlogCategory[]>([]);
  const [tags, setTags] = useState<BlogTag[]>([]);
  const [authors, setAuthors] = useState<BlogAuthor[]>([]);
  const [revisions, setRevisions] = useState<BlogRevisionPublic[]>([]);
  const [selectionRange, setSelectionRange] = useState<{
    start: number;
    end: number;
  } | null>(null);
  const [busyAction, setBusyAction] = useState(false);
  const [titleIdeasOpen, setTitleIdeasOpen] = useState(false);
  const hydratedLocal = useRef(false);

  const { saveNow } = useBlogStudioAutosave({
    enabled: true,
  });

  useEffect(() => {
    void (async () => {
      try {
        const [c, t, a] = await Promise.all([
          fetchAdminBlogCategories(),
          fetchAdminBlogTags(),
          fetchAdminBlogAuthors(),
        ]);
        setCategories(c);
        setTags(t);
        setAuthors(a);
      } catch {
        /* empty catalogs */
      }
    })();
  }, []);

  useEffect(() => {
    if (mode !== "new" || hydratedLocal.current || initialPost) return;
    hydratedLocal.current = true;
    const local = readLocalStudioDraft();
    if (!local) return;
    if (
      !window.confirm(
        "Recover an unsaved Blog Studio draft from this browser?",
      )
    ) {
      return;
    }
    studio.patch({
      title: local.title || "",
      slug: local.slug || "",
      excerpt: local.excerpt || "",
      body: local.body || studio.body,
      coverUrl: local.coverUrl || "",
      seoTitle: local.seoTitle || "",
      seoDescription: local.seoDescription || "",
      focusKeyword: local.focusKeyword || "",
      secondaryKeywords: local.secondaryKeywords || [],
      brief: (local.brief as BlogContentBrief) || studio.brief,
      outline: (local.outline as BlogOutline) || studio.outline,
      faqs: (local.faqs as BlogFaqItem[]) || [],
      dirty: true,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- hydrate once
  }, [mode, initialPost]);

  useEffect(() => {
    if (!studio.slug.trim()) {
      studio.patch({ slugOk: null });
      return;
    }
    const t = setTimeout(() => {
      void checkBlogSlug(studio.slug, studio.postId || undefined)
        .then((r) => studio.patch({ slugOk: r.available }))
        .catch(() => studio.patch({ slugOk: null }));
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studio.slug, studio.postId]);

  const refreshRevisions = useCallback(async () => {
    if (!studio.postId) return;
    try {
      const list = await studioListRevisions(studio.postId);
      setRevisions(list);
    } catch {
      /* endpoint may not exist yet */
    }
  }, [studio.postId]);

  useEffect(() => {
    void refreshRevisions();
  }, [refreshRevisions]);

  const sections = useMemo(
    () => parseMarkdownH2Sections(studio.body),
    [studio.body],
  );

  const blockDocumentMode = isBlockDocumentMode(
    studio.contentDocument,
    studio.contentMode,
  );

  const completed = useMemo(
    () => ({
      brief: Boolean(studio.brief.topic?.trim()),
      seo_brief: Boolean(studio.seoBrief),
      titles: Boolean(studio.title.trim()),
      outline: Boolean(studio.outline.approved || studio.outline.sections.length),
      draft: studio.body.trim().length > 80,
      review: Boolean(studio.qualityReview || studio.factClaims.length),
      publish: studio.status === "published",
    }),
    [studio],
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
      if (studio.isCancelled()) {
        toast.push({ tone: "warning", title: "Generation cancelled" });
        return null;
      }
      return result;
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "AI request failed",
      });
      return null;
    } finally {
      studio.endGeneration();
    }
  }

  async function handleSeoBrief() {
    const res = await runAi("seo_brief", "Generating SEO brief…", () =>
      studioGenerateSeoBrief(studioBase(studio)),
    );
    if (!res) return;
    studio.patch({ seoBrief: res, workflowStep: "seo_brief" });
    if (res.primary_keyword) {
      studio.setBrief({
        ...studio.brief,
        primary_keyword: res.primary_keyword,
        secondary_keywords:
          res.secondary_keywords || studio.brief.secondary_keywords,
        search_intent: res.search_intent || studio.brief.search_intent,
      });
      studio.patch({
        focusKeyword: res.primary_keyword,
        secondaryKeywords:
          res.secondary_keywords || studio.secondaryKeywords,
      });
    }
    if (res.proposed_slug && confirmOverwrite("slug", studio.slug)) {
      studio.patch({ slug: res.proposed_slug, dirty: true });
    }
    if (
      (res.meta_title || res.meta_description) &&
      confirmOverwrite(
        "SEO title/description",
        `${studio.seoTitle}${studio.seoDescription}`,
      )
    ) {
      studio.patch({
        seoTitle: res.meta_title || studio.seoTitle,
        seoDescription: res.meta_description || studio.seoDescription,
        dirty: true,
      });
    }
    toast.push({ tone: "success", title: "SEO brief ready" });
  }

  async function handleTitles() {
    const res = await runAi("titles", "Generating title options…", () =>
      studioGenerateTitles(studioBase(studio)),
    );
    if (!res) return;
    const titles = normalizeTitleSuggestions(res);
    studio.patch({
      titleSuggestions: titles,
      workflowStep: "titles",
    });
    setTitleIdeasOpen(true);
  }

  async function handleOutline() {
    const res = await runAi("outline", "Building outline…", () =>
      studioGenerateOutline(studioBase(studio)),
    );
    if (!res) return;
    const withIds: BlogOutline = {
      ...res,
      sections: (res.sections || []).map((s) => ({
        ...s,
        id: s.id || newSectionId(),
      })),
      approved: false,
    };
    studio.setOutline(withIds);
    studio.patch({ workflowStep: "outline" });
    toast.push({ tone: "success", title: "Outline generated" });
  }

  async function handleOutlineSection(sectionId: string) {
    const res = await runAi("outline", "Regenerating outline section…", () =>
      studioRegenerateOutlineSection({
        ...studioBase(studio),
        section_id: sectionId,
        section: studio.outline.sections.find((s) => s.id === sectionId),
      }),
    );
    if (!res) return;
    if ("sections" in res && Array.isArray(res.sections)) {
      studio.setOutline(res as BlogOutline);
    } else {
      studio.setOutline({
        ...studio.outline,
        sections: studio.outline.sections.map((s) =>
          s.id === sectionId ? { ...s, ...(res as object) } : s,
        ),
      });
    }
  }

  async function handleFullDraft() {
    if (!studio.outline.approved) {
      const ok = window.confirm(
        "Outline is not marked approved. Generate full draft anyway?",
      );
      if (!ok) return;
    }
    const res = await runAi("draft", "Writing draft section by section…", () =>
      studioGenerateFullDraft(studioBase(studio)),
    );
    if (!res) return;
    const md =
      res.body_markdown ||
      (res.sections || [])
        .map(
          (s) =>
            `## ${s.heading}\n\n${s.body || ""}${
              s.bullets?.length
                ? `\n\n${s.bullets.map((b) => `- ${b}`).join("\n")}`
                : ""
            }`,
        )
        .join("\n\n");
    if (!md.trim()) {
      toast.push({ tone: "warning", title: "Draft returned empty" });
      return;
    }
    if (
      studio.body.trim().length > 40 &&
      !window.confirm(
        "Replace the current article body with the generated draft?",
      )
    ) {
      return;
    }
    studio.setBody(md.trim() + "\n");
    studio.patch({ workflowStep: "draft" });
    if (res.failed_section_ids?.length) {
      toast.push({
        tone: "warning",
        title: `Draft partial — failed: ${res.failed_section_ids.join(", ")}`,
      });
    } else {
      toast.push({ tone: "success", title: "Draft generated" });
    }
  }

  async function handleSectionAi(
    index: number,
    action: "regenerate" | "rewrite" | "expand" | "shorter",
  ) {
    const sec = sections[index];
    if (!sec) return;
    if (studio.lockedSectionHeadings.includes(sec.heading)) {
      toast.push({ tone: "warning", title: "Section is locked" });
      return;
    }
    if (action === "regenerate") {
      const outlineSec =
        studio.outline.sections.find((s) => s.heading === sec.heading) ||
        studio.outline.sections[index];
      const res = await runAi("section", `Writing section ${index + 1}…`, () =>
        studioGenerateSection({
          ...studioBase(studio),
          section_id: outlineSec?.id || `md-${index}`,
          section: outlineSec || {
            id: `md-${index}`,
            heading: sec.heading,
            key_point: sec.body.slice(0, 200),
          },
        }),
      );
      if (!res) return;
      const body =
        res.section?.body ||
        res.section?.markdown ||
        res.body ||
        res.markdown ||
        "";
      if (!body) return;
      studio.setBody(
        replaceSectionAt(studio.body, index, {
          heading: res.section?.heading || sec.heading,
          body,
        }),
      );
      return;
    }
    const rewriteAction: RewriteAction =
      action === "expand"
        ? "expand"
        : action === "shorter"
          ? "shorter"
          : "rewrite";
    const res = await runAi("rewrite", `Rewriting section ${index + 1}…`, () =>
      studioRewriteSelection({
        ...studioBase(studio),
        selection: sec.body || sec.heading,
        action: rewriteAction,
      }),
    );
    if (!res) return;
    const proposed = res.rewritten || res.suggestion || res.text || "";
    if (!proposed) return;
    studio.setSuggestion({
      original: sec.body,
      proposed,
      action: rewriteAction,
      start: sec.start,
      end: sec.end,
    });
  }

  async function handleInlineRewrite(action: RewriteAction) {
    if (!selectionRange || selectionRange.start === selectionRange.end) return;
    const { start, end } = selectionRange;
    const selected = studio.body.slice(start, end);
    if (!selected) return;
    const res = await runAi("rewrite", "Rewriting selection…", () =>
      studioRewriteSelection({
        ...studioBase(studio),
        selection: selected,
        action,
        tone: studio.brief.tone,
      }),
    );
    if (!res) return;
    const proposed = res.rewritten || res.suggestion || res.text || "";
    if (!proposed) return;
    studio.setSuggestion({
      original: selected,
      proposed,
      action,
      start,
      end,
    });
  }

  function applySuggestion(mode: "apply" | "insert" | "replace") {
    const s = studio.suggestion;
    if (!s) return;
    if (mode === "insert") {
      const next =
        studio.body.slice(0, s.end) +
        "\n\n" +
        s.proposed +
        studio.body.slice(s.end);
      studio.setBody(next);
    } else {
      const next =
        studio.body.slice(0, s.start) + s.proposed + studio.body.slice(s.end);
      studio.setBody(next);
    }
    studio.setSuggestion(null);
  }

  async function handleSeoScore() {
    const res = await runAi("seo_score", "Scoring SEO…", () =>
      studioSeoScore({
        ...studioBase(studio),
        cover_url: studio.coverUrl,
        seo_title: studio.seoTitle,
        seo_description: studio.seoDescription,
      }),
    );
    if (res) studio.patch({ seoScore: res });
  }

  async function handlePublish() {
    setBusyAction(true);
    try {
      await saveNow();
      if (!studio.postId) {
        toast.push({ tone: "danger", title: "Save a draft before publishing" });
        return;
      }
      const post = await publishAdminBlogPost(studio.postId);
      studio.patch({ status: post.status, dirty: false });
      clearLocalStudioDraft();
      toast.push({ tone: "success", title: "Published" });
      studio.patch({ workflowStep: "publish" });
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Publish failed",
      });
    } finally {
      setBusyAction(false);
    }
  }

  const previewHtml = useMemo(() => {
    if (studio.bodyHtml && studio.previewOpen && !studio.dirty) {
      return studio.bodyHtml;
    }
    return simpleMarkdownToHtml(studio.body);
  }, [studio.body, studio.bodyHtml, studio.previewOpen, studio.dirty]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Blog AI Studio"
      title={mode === "new" ? "New post" : studio.title || "Edit post"}
      description="AI drafts and suggests — you review, confirm, and publish."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={studio.status === "published" ? "success" : "neutral"}>
            {studio.status}
          </Badge>
          {studio.autosaveStatus === "saving" ? (
            <span className="text-xs text-muted-foreground">Saving…</span>
          ) : studio.autosaveStatus === "saved" ? (
            <span className="text-xs text-muted-foreground">Saved</span>
          ) : studio.autosaveStatus === "failed" ? (
            <span className="text-xs text-danger">Save failed</span>
          ) : null}
          {studio.status === "published" && studio.slug ? (
            <Link
              href={`/blog/${studio.slug}`}
              target="_blank"
              className="text-sm font-semibold text-primary"
            >
              Public view
            </Link>
          ) : null}
          <Link href="/admin/blog" className="text-sm font-semibold text-primary">
            Back
          </Link>
        </div>
      }
    >
      <BlogStudioShell
        leftOpen={leftOpen}
        rightOpen={rightOpen}
        onToggleLeft={() => setLeftOpen((v) => !v)}
        onToggleRight={() => setRightOpen((v) => !v)}
        left={
          <>
            <BlogContentBriefPanel
              brief={studio.brief}
              disabled={studio.generating}
              onChange={(brief) => {
                studio.setBrief(brief);
                if (brief.primary_keyword) {
                  studio.patch({ focusKeyword: brief.primary_keyword });
                }
                if (brief.secondary_keywords) {
                  studio.patch({
                    secondaryKeywords: brief.secondary_keywords,
                  });
                }
              }}
            />
            <BlogAiWorkflow
              current={studio.workflowStep}
              completed={completed}
              onSelect={(id: BlogWorkflowStepId) =>
                studio.patch({ workflowStep: id })
              }
            />
            <div className="flex flex-wrap gap-1">
              <Button
                size="sm"
                variant="secondary"
                disabled={studio.generating}
                onClick={() => void handleSeoBrief()}
              >
                SEO brief
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={studio.generating}
                onClick={() => void handleTitles()}
              >
                Titles
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={studio.generating}
                onClick={() => void handleOutline()}
              >
                Outline
              </Button>
              <Button
                size="sm"
                disabled={studio.generating}
                onClick={() => void handleFullDraft()}
              >
                Full draft
              </Button>
            </div>
            <AiGenerationProgress
              stage={studio.generationStage}
              message={studio.generationMessage}
              busy={studio.generating}
              onCancel={studio.cancelGeneration}
            />
            <BlogSettingsSummary
              status={studio.status}
              categoryName={
                categories.find((c) => c.id === studio.categoryId)?.name
              }
              authorName={
                authors.find((a) => a.id === studio.authorId)?.display_name
              }
              tagCount={studio.tagIds.length}
              featured={studio.featured}
              autosaveStatus={studio.autosaveStatus}
              lastSavedAt={studio.lastSavedAt}
              seoScore={studio.seoScore}
              workflowStep={studio.workflowStep}
            />
            <BlogSeoScoreStatus
              seoScore={studio.seoScore}
              busy={studio.generating}
              onRefresh={() => void handleSeoScore()}
            />
          </>
        }
        main={
          <>
            <Alert tone="info" title="Markdown editor">
              Headings (# ## ###), lists, quotes, links, images, code fences, and
              embeds ::cta / ::event / ::host. AI never silently overwrites
              selected text.
            </Alert>
            <Input
              label="Title"
              value={studio.title}
              onChange={(e) => {
                const title = e.target.value;
                const patch: Record<string, unknown> = {
                  title,
                  dirty: true,
                };
                if (!studio.slug) {
                  patch.slug = title
                    .toLowerCase()
                    .replace(/[^a-z0-9]+/g, "-")
                    .replace(/^-|-$/g, "");
                }
                if (!studio.brief.topic) {
                  studio.setBrief({ ...studio.brief, topic: title });
                }
                studio.patch(patch);
              }}
            />
            {titleIdeasOpen && studio.titleSuggestions.length > 0 ? (
              <div className="space-y-2 rounded-[var(--radius-md)] border border-border bg-surface px-3 py-3">
                <p className="text-sm font-semibold">Title suggestions</p>
                <ul className="space-y-2">
                  {studio.titleSuggestions.map((t) => (
                    <li key={t.title}>
                      <button
                        type="button"
                        className="w-full rounded-[var(--radius-sm)] border border-border px-3 py-2 text-left text-sm hover:border-primary"
                        onClick={() => {
                          if (!confirmOverwrite("title", studio.title)) return;
                          studio.patch({ title: t.title, dirty: true });
                          setTitleIdeasOpen(false);
                        }}
                      >
                        <span className="font-medium">{t.title}</span>
                        {t.angle ? (
                          <span className="mt-0.5 block text-xs text-muted-foreground">
                            {t.angle}
                          </span>
                        ) : null}
                        {t.warning ? (
                          <span className="mt-0.5 block text-xs text-amber-700 dark:text-amber-400">
                            {t.warning}
                          </span>
                        ) : null}
                      </button>
                    </li>
                  ))}
                </ul>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setTitleIdeasOpen(false)}
                >
                  Dismiss
                </Button>
              </div>
            ) : null}
            <Textarea
              label="Excerpt"
              rows={2}
              value={studio.excerpt}
              onChange={(e) =>
                studio.patch({ excerpt: e.target.value, dirty: true })
              }
            />
            <BlogInlineAiMenu
              visible={Boolean(
                selectionRange && selectionRange.start !== selectionRange.end,
              )}
              busy={studio.generating}
              onAction={(action) => void handleInlineRewrite(action)}
            />
            <BlogEditorShell
              postId={studio.postId}
              title={studio.title}
              excerpt={studio.excerpt}
              bodyHtml={studio.bodyHtml}
              initialDocument={studio.contentDocument}
              initialEditorMode={studio.editorMode}
              initialHeroSettings={studio.heroSettings}
              contentVersion={studio.contentVersion}
              autosaveStatus={studio.autosaveStatus}
              isNew={mode === "new" && !studio.postId}
              onDocumentChange={(doc, meta) => {
                studio.setContentDocument(doc);
                studio.patch({ editorMode: meta.editorMode, dirty: true });
              }}
              onManualSave={() => void saveNow()}
              onPublish={() => void handlePublish()}
              onAiBlock={() => {
                toast.push({
                  tone: "info",
                  title: "Use the AI assistant panel for optional help.",
                });
              }}
              onCreationStarted={(choice) => {
                if (choice === "ai") {
                  studio.patch({ workflowStep: "brief" });
                }
              }}
            />
            <AiSuggestionDiff
              suggestion={studio.suggestion}
              onApply={() => applySuggestion("apply")}
              onInsertBelow={() => applySuggestion("insert")}
              onReplace={() => applySuggestion("replace")}
              onDiscard={() => studio.setSuggestion(null)}
            />
            {!blockDocumentMode ? (
            <div className="space-y-2 rounded-[var(--radius-md)] border border-border bg-surface px-3 py-3">
              <p className="text-sm font-semibold">Section controls (legacy markdown)</p>
              <BlogSectionToolbar
                sections={sections}
                lockedHeadings={studio.lockedSectionHeadings}
                busy={studio.generating}
                onRegenerate={(i) => void handleSectionAi(i, "regenerate")}
                onRewrite={(i) => void handleSectionAi(i, "rewrite")}
                onExpand={(i) => void handleSectionAi(i, "expand")}
                onShorten={(i) => void handleSectionAi(i, "shorter")}
                onMove={(i, dir) => studio.setBody(moveSection(studio.body, i, dir))}
                onDelete={(i) => {
                  if (window.confirm("Delete this section from the article?")) {
                    studio.setBody(deleteSection(studio.body, i));
                  }
                }}
                onDuplicate={(i) =>
                  studio.setBody(duplicateSection(studio.body, i))
                }
                onAddBelow={(i) =>
                  studio.setBody(insertSectionBelow(studio.body, i))
                }
                onToggleLock={(heading) => studio.toggleSectionLock(heading)}
              />
            </div>
            ) : null}
            <BlogOutlineEditor
              outline={studio.outline}
              busy={studio.generating}
              onChange={(o) => studio.setOutline(o)}
              onRegenerateAll={() => void handleOutline()}
              onRegenerateSection={(id) => void handleOutlineSection(id)}
            />
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="secondary"
                disabled={!studio.outline.sections.length}
                onClick={() => {
                  if (
                    studio.body.trim().length > 40 &&
                    !window.confirm(
                      "Insert outline headings into the article body?",
                    )
                  ) {
                    return;
                  }
                  studio.setBody(outlineToMarkdown(studio.outline));
                }}
              >
                Insert outline into editor
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() =>
                  studio.patch({ previewOpen: !studio.previewOpen })
                }
              >
                {studio.previewOpen ? "Hide preview" : "Preview"}
              </Button>
            </div>
            {studio.previewOpen ? (
              <div className="space-y-2 rounded-[var(--radius-md)] border border-border bg-surface-muted p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  In-studio preview (not publicly indexable)
                </p>
                <h1 className="font-display text-2xl font-extrabold text-heading">
                  {studio.title || "Untitled"}
                </h1>
                {studio.excerpt ? (
                  <p className="text-sm text-muted-foreground">{studio.excerpt}</p>
                ) : null}
                <div
                  className="prose prose-sm dark:prose-invert max-w-none"
                  dangerouslySetInnerHTML={{ __html: previewHtml }}
                />
                {studio.faqs.length > 0 ? (
                  <div className="mt-6 space-y-2">
                    <h2 className="text-lg font-bold">FAQs</h2>
                    {studio.faqs.map((f) => (
                      <div key={f.id}>
                        <p className="font-semibold">{f.question}</p>
                        <p className="text-sm text-muted-foreground">{f.answer}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
            <BlogFaqEditor
              faqs={studio.faqs}
              busy={studio.generating}
              onChange={(faqs) => studio.setFaqs(faqs)}
              onGenerate={() =>
                void (async () => {
                  const res = await runAi("faqs", "Generating FAQs…", () =>
                    studioGenerateFaqs(studioBase(studio)),
                  );
                  if (!res) return;
                  const faqs = normalizeFaqs(res).map((f) => ({
                    ...f,
                    id: f.id || newFaqId(),
                  }));
                  studio.setFaqs(faqs);
                })()
              }
            />
            <BlogQualityReviewPanel
              review={studio.qualityReview}
              busy={studio.generating}
              onRun={() =>
                void (async () => {
                  const res = await runAi("review", "Reviewing article…", () =>
                    studioReviewArticle(studioBase(studio)),
                  );
                  if (res) {
                    studio.patch({
                      qualityReview: res,
                      workflowStep: "review",
                    });
                  }
                })()
              }
            />
            <BlogFactReviewPanel
              claims={studio.factClaims}
              busy={studio.generating}
              onRun={() =>
                void (async () => {
                  const res = await runAi("facts", "Reviewing claims…", () =>
                    studioFactReview(studioBase(studio)),
                  );
                  if (res) {
                    studio.patch({ factClaims: normalizeFactClaims(res) });
                  }
                })()
              }
            />
            <BlogInternalLinksPanel
              suggestions={studio.internalLinks}
              busy={studio.generating}
              onRun={() =>
                void (async () => {
                  const res = await runAi("links", "Finding links…", () =>
                    studioSuggestInternalLinks(studioBase(studio)),
                  );
                  if (res) {
                    studio.patch({
                      internalLinks: normalizeInternalLinks(res),
                    });
                  }
                })()
              }
              onInsert={(s: BlogInternalLinkSuggestion) => {
                const anchor = s.suggested_anchor || s.target_title || "Learn more";
                const md = `[${anchor}](${s.target_url})`;
                studio.setBody((prev) => `${prev.trim()}\n\n${md}\n`);
              }}
              onDismiss={(s) => {
                studio.patch({
                  internalLinks: studio.internalLinks.map((x) =>
                    x.target_url === s.target_url &&
                    x.suggested_anchor === s.suggested_anchor
                      ? { ...x, dismissed: true }
                      : x,
                  ),
                });
              }}
            />
            {studio.postId ? (
              <BlogVersionHistory
                revisions={revisions}
                busy={busyAction || studio.generating}
                onRefresh={() => void refreshRevisions()}
                onPreview={(r) =>
                  void (async () => {
                    try {
                      const full = await studioGetRevision(
                        studio.postId!,
                        r.id,
                      );
                      window.alert(
                        `Revision preview\n\nTitle: ${full.title || r.title || ""}\n\n${(full.body || "").slice(0, 800)}`,
                      );
                    } catch {
                      window.alert(
                        `Revision ${r.id}\n${r.summary || r.action_type || ""}`,
                      );
                    }
                  })()
                }
                onRestore={(r) =>
                  void (async () => {
                    setBusyAction(true);
                    try {
                      const post = await studioRestoreRevision(
                        studio.postId!,
                        r.id,
                      );
                      hydrateFromPost(studio, post);
                      toast.push({ tone: "success", title: "Revision restored" });
                      await refreshRevisions();
                    } catch (e) {
                      toast.push({
                        tone: "danger",
                        title:
                          e instanceof ApiError
                            ? e.message
                            : "Restore failed",
                      });
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
                      await studioCheckpointRevision(studio.postId, {
                        summary: "Manual checkpoint",
                      });
                      await refreshRevisions();
                      toast.push({ tone: "success", title: "Checkpoint saved" });
                    } catch (e) {
                      toast.push({
                        tone: "danger",
                        title:
                          e instanceof ApiError
                            ? e.message
                            : "Checkpoint failed",
                      });
                    } finally {
                      setBusyAction(false);
                    }
                  })()
                }
              />
            ) : null}
          </>
        }
        right={
          <>
            <BlogSeoPanel
              slug={studio.slug}
              seoTitle={studio.seoTitle}
              seoDescription={studio.seoDescription}
              canonicalUrl={studio.canonicalUrl}
              excerpt={studio.excerpt}
              ogTitle={studio.ogTitle}
              ogImageUrl={studio.ogImageUrl}
              socialShareText={studio.socialShareText}
              focusKeyword={studio.focusKeyword}
              secondaryKeywords={studio.secondaryKeywords}
              slugOk={studio.slugOk}
              seoScore={studio.seoScore}
              onChange={(patch) =>
                studio.patch({ ...patch, dirty: true } as Partial<
                  typeof studio
                >)
              }
            />
            <BlogImageAssistant
              coverUrl={studio.coverUrl}
              imagePrompt={studio.imagePrompt}
              busy={studio.generating}
              onCoverChange={(url) =>
                studio.patch({ coverUrl: url, dirty: true })
              }
              onGenerate={() =>
                void (async () => {
                  const res = await runAi(
                    "image",
                    "Generating image prompt…",
                    () => studioGenerateImagePrompt(studioBase(studio)),
                  );
                  if (res) studio.patch({ imagePrompt: res });
                })()
              }
              onApplyAltCaption={(alt, caption) => {
                const note = [
                  studio.adminNotes,
                  alt ? `Image alt: ${alt}` : "",
                  caption ? `Caption: ${caption}` : "",
                ]
                  .filter(Boolean)
                  .join("\n");
                studio.patch({ adminNotes: note, dirty: true });
              }}
            />
            <BlogPublishPanel
              status={studio.status}
              featured={studio.featured}
              scheduledAt={studio.scheduledAt}
              categoryId={studio.categoryId}
              authorId={studio.authorId}
              tagIds={studio.tagIds}
              categories={categories}
              authors={authors}
              tags={tags}
              adminNotes={studio.adminNotes}
              autosaveStatus={studio.autosaveStatus}
              busy={busyAction || studio.generating}
              previewOpen={studio.previewOpen}
              postId={studio.postId}
              slug={studio.slug}
              onChange={(patch) =>
                studio.patch({ ...patch, dirty: true } as Partial<
                  typeof studio
                >)
              }
              onToggleTag={(id) => {
                const on = studio.tagIds.includes(id);
                studio.patch({
                  tagIds: on
                    ? studio.tagIds.filter((x) => x !== id)
                    : [...studio.tagIds, id],
                  dirty: true,
                });
              }}
              onSaveDraft={() => void saveNow()}
              onTogglePreview={() =>
                void (async () => {
                  const next = !studio.previewOpen;
                  studio.patch({ previewOpen: next });
                  if (next && studio.postId) {
                    try {
                      const p = await studioPreviewPost(studio.postId);
                      if (p.body_html) {
                        studio.patch({ bodyHtml: p.body_html });
                      }
                    } catch {
                      /* client markdown preview fallback */
                    }
                  }
                })()
              }
              onPublish={() => void handlePublish()}
              onUnpublish={() =>
                void (async () => {
                  if (!studio.postId) return;
                  setBusyAction(true);
                  try {
                    const post = await unpublishAdminBlogPost(studio.postId);
                    studio.patch({ status: post.status });
                    toast.push({ tone: "success", title: "Unpublished" });
                  } catch (e) {
                    toast.push({
                      tone: "danger",
                      title:
                        e instanceof ApiError ? e.message : "Unpublish failed",
                    });
                  } finally {
                    setBusyAction(false);
                  }
                })()
              }
              onArchive={() =>
                void (async () => {
                  if (!studio.postId) return;
                  setBusyAction(true);
                  try {
                    await deleteAdminBlogPost(studio.postId);
                    toast.push({ tone: "success", title: "Archived" });
                    router.push("/admin/blog");
                  } catch (e) {
                    toast.push({
                      tone: "danger",
                      title:
                        e instanceof ApiError ? e.message : "Archive failed",
                    });
                  } finally {
                    setBusyAction(false);
                  }
                })()
              }
            />
            <BlogPostAnalyticsPanel postId={studio.postId} />
          </>
        }
      />
    </DashboardShell>
  );
}

function hydrateFromPost(
  studio: ReturnType<typeof useBlogStudio>,
  post: BlogPost,
) {
  const p = post as BlogPost & {
    content_version?: number;
    focus_keyword?: string | null;
    secondary_keywords?: string[] | null;
    social_share_text?: string | null;
    og_title?: string | null;
    studio_brief?: BlogContentBrief | null;
    studio_outline?: BlogOutline | null;
    faqs?: BlogFaqItem[] | null;
  };
  studio.patch({
    postId: post.id,
    title: post.title,
    slug: post.slug,
    excerpt: post.excerpt || "",
    body: post.body,
    coverUrl: post.cover_url || "",
    seoTitle: post.seo_title || "",
    seoDescription: post.seo_description || "",
    canonicalUrl: post.canonical_url || "",
    ogImageUrl: post.og_image_url || "",
    ogTitle: p.og_title || "",
    socialShareText: p.social_share_text || "",
    focusKeyword: p.focus_keyword || "",
    secondaryKeywords: p.secondary_keywords || [],
    featured: post.is_featured,
    categoryId: post.category?.id || "",
    authorId: post.author?.id || "",
    tagIds: (post.tags || []).map((t) => t.id),
    scheduledAt: post.scheduled_at
      ? new Date(post.scheduled_at).toISOString().slice(0, 16)
      : "",
    adminNotes: post.admin_notes || "",
    status: post.status,
    contentVersion: p.content_version ?? 1,
    bodyHtml: post.body_html,
    contentDocument: parseContentDocument(
      (p as { content_document?: Record<string, unknown> }).content_document,
      post.body,
    ),
    contentMode: resolveContentMode(
      parseContentDocument(
        (p as { content_document?: Record<string, unknown> }).content_document,
        post.body,
      ),
      (p as { content_mode?: string }).content_mode as
        | import("@/lib/blog-document").ContentMode
        | undefined,
    ),
    editorMode:
      ((p as { editor_mode?: string }).editor_mode as "standard" | "layout") ||
      "standard",
    heroSettings:
      ((p as { hero_settings?: Record<string, unknown> }).hero_settings as
        | import("@/lib/blog-document").HeroSettings
        | undefined) ?? null,
    brief: p.studio_brief || studio.brief,
    outline: p.studio_outline || studio.outline,
    faqs: p.faqs || [],
    dirty: false,
  });
}

export function BlogStudioPage({
  mode,
  initialPost,
}: {
  mode: "new" | "edit";
  initialPost?: BlogPost | null;
}) {
  const seed = initialPost
    ? (() => {
        const p = initialPost as BlogPost & {
          content_version?: number;
          focus_keyword?: string | null;
          secondary_keywords?: string[] | null;
          social_share_text?: string | null;
          og_title?: string | null;
          studio_brief?: BlogContentBrief | null;
          studio_outline?: BlogOutline | null;
          faqs?: BlogFaqItem[] | null;
        };
        return {
          postId: initialPost.id,
          title: initialPost.title,
          slug: initialPost.slug,
          excerpt: initialPost.excerpt || "",
          body: initialPost.body,
          coverUrl: initialPost.cover_url || "",
          seoTitle: initialPost.seo_title || "",
          seoDescription: initialPost.seo_description || "",
          canonicalUrl: initialPost.canonical_url || "",
          ogImageUrl: initialPost.og_image_url || "",
          ogTitle: p.og_title || "",
          socialShareText: p.social_share_text || "",
          focusKeyword: p.focus_keyword || "",
          secondaryKeywords: p.secondary_keywords || [],
          featured: initialPost.is_featured,
          categoryId: initialPost.category?.id || "",
          authorId: initialPost.author?.id || "",
          tagIds: (initialPost.tags || []).map((t) => t.id),
          scheduledAt: initialPost.scheduled_at
            ? new Date(initialPost.scheduled_at).toISOString().slice(0, 16)
            : "",
          adminNotes: initialPost.admin_notes || "",
          status: initialPost.status,
          contentVersion: p.content_version ?? 1,
          bodyHtml: initialPost.body_html,
          contentDocument: parseContentDocument(
            (p as { content_document?: Record<string, unknown> }).content_document,
            initialPost.body,
          ),
          editorMode:
            ((p as { editor_mode?: string }).editor_mode as "standard" | "layout") ||
            "standard",
          heroSettings:
            ((p as { hero_settings?: Record<string, unknown> }).hero_settings as
              | import("@/lib/blog-document").HeroSettings
              | undefined) ?? null,
          brief: p.studio_brief || undefined,
          outline: p.studio_outline || undefined,
          faqs: p.faqs || undefined,
        };
      })()
    : undefined;

  return (
    <BlogStudioProvider initial={seed}>
      <BlogStudioInner mode={mode} initialPost={initialPost} />
    </BlogStudioProvider>
  );
}
