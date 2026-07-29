"use client";
// BlogAiDrawer — right-side AI assistant panel, context-aware per tab

import { Button } from "@/components/ui";
import { useBlogStudio } from "@/components/blog/studio/BlogStudioProvider";
import {
  AiGenerationProgress,
} from "@/components/blog/studio/AiGenerationProgress";
import { cn } from "@/lib/cn";
import type { WorkspaceTab } from "@/lib/blog-workspace";
import {
  studioGenerateSeoBrief,
  studioGenerateTitles,
  studioGenerateOutline,
} from "@/lib/blog-studio-api";
import { normalizeTitleSuggestions } from "@/lib/blog-studio-api";
import { ApiError } from "@/lib/api";
import { useToast } from "@/components/ui";
import { newSectionId } from "@/components/blog/studio/types";
import type { BlogOutline } from "@/components/blog/studio/types";

const TAB_TOOLS: Record<WorkspaceTab, { id: string; label: string; description: string }[]> = {
  plan: [
    { id: "seo_brief", label: "Generate SEO brief", description: "Suggests keywords, angle & structure" },
    { id: "titles", label: "Suggest titles", description: "Generate title options from your brief" },
    { id: "outline", label: "Build outline", description: "Create a section outline from the brief" },
  ],
  write: [
    { id: "titles", label: "Suggest titles", description: "More title options" },
    { id: "outline", label: "Regenerate outline", description: "Rebuild the outline" },
  ],
  design: [
    { id: "outline", label: "Rebuild outline", description: "Sync outline from document structure" },
  ],
  seo: [
    { id: "seo_brief", label: "Suggest metadata", description: "Generate meta title & description" },
  ],
  review: [
    { id: "seo_brief", label: "SEO brief", description: "Refresh SEO recommendations" },
  ],
  publish: [],
};

type Props = {
  open: boolean;
  onClose: () => void;
  activeTab: WorkspaceTab;
};

export function BlogAiDrawer({ open, onClose, activeTab }: Props) {
  const studio = useBlogStudio();
  const toast = useToast();

  const tools = TAB_TOOLS[activeTab] ?? [];

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

  async function runTool(id: string) {
    if (id === "seo_brief") {
      const res = await runAi("seo_brief", "Generating SEO brief…", () =>
        studioGenerateSeoBrief(studioBase()),
      );
      if (!res) return;
      studio.patch({ seoBrief: res });
      if (res.primary_keyword) {
        studio.setBrief({ ...studio.brief, primary_keyword: res.primary_keyword });
        studio.patch({ focusKeyword: res.primary_keyword });
      }
      if (res.meta_title) studio.patch({ seoTitle: res.meta_title, dirty: true });
      if (res.meta_description) studio.patch({ seoDescription: res.meta_description, dirty: true });
      toast.push({ tone: "success", title: "SEO brief generated" });
    } else if (id === "titles") {
      const res = await runAi("titles", "Generating title options…", () =>
        studioGenerateTitles(studioBase()),
      );
      if (!res) return;
      studio.patch({ titleSuggestions: normalizeTitleSuggestions(res) });
      toast.push({ tone: "success", title: "Title suggestions ready" });
    } else if (id === "outline") {
      const res = await runAi("outline", "Building outline…", () =>
        studioGenerateOutline(studioBase()),
      );
      if (!res) return;
      const withIds: BlogOutline = {
        ...res,
        sections: (res.sections || []).map((s: { id?: string; heading: string }) => ({
          ...s,
          id: s.id || newSectionId(),
        })),
        approved: false,
      };
      studio.setOutline(withIds);
      toast.push({ tone: "success", title: "Outline generated" });
    }
  }

  return (
    <aside
      className={cn(
        "fixed right-0 top-[var(--header-height,4rem)] bottom-0 z-40 flex flex-col bg-card border-l border-border shadow-lg transition-transform duration-200",
        open ? "translate-x-0 w-80" : "translate-x-full w-80",
      )}
    >
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="text-sm font-semibold">AI Assistant</span>
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground"
          onClick={onClose}
          aria-label="Close AI drawer"
        >
          <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 4l8 8M12 4l-8 8" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {tools.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No AI tools available for this tab.
          </p>
        ) : (
          tools.map((tool) => (
            <div
              key={tool.id}
              className="rounded-lg border border-border bg-surface p-3 space-y-2"
            >
              <p className="text-sm font-semibold">{tool.label}</p>
              <p className="text-xs text-muted-foreground">{tool.description}</p>
              <Button
                size="sm"
                variant="secondary"
                disabled={studio.generating}
                onClick={() => void runTool(tool.id)}
              >
                Run
              </Button>
            </div>
          ))
        )}

        {/* Title suggestions */}
        {studio.titleSuggestions.length > 0 ? (
          <div className="rounded-lg border border-border bg-surface p-3 space-y-2">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Title suggestions
            </p>
            <ul className="space-y-1">
              {studio.titleSuggestions.map((t) => (
                <li key={t.title}>
                  <button
                    type="button"
                    className="w-full rounded border border-border px-2 py-1.5 text-left text-sm hover:border-primary"
                    onClick={() => {
                      if (studio.title && !window.confirm("Replace current title?")) return;
                      studio.patch({ title: t.title, dirty: true });
                    }}
                  >
                    {t.title}
                    {t.angle ? (
                      <span className="block text-xs text-muted-foreground mt-0.5">{t.angle}</span>
                    ) : null}
                  </button>
                </li>
              ))}
            </ul>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => studio.patch({ titleSuggestions: [] })}
            >
              Dismiss
            </Button>
          </div>
        ) : null}

        <AiGenerationProgress
          stage={studio.generationStage}
          message={studio.generationMessage}
          busy={studio.generating}
          onCancel={studio.cancelGeneration}
        />
      </div>
    </aside>
  );
}
