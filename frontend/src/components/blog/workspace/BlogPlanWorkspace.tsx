"use client";
// BlogPlanWorkspace — Plan tab: content brief + title + outline

import { useEffect, useState } from "react";
import { Button, Input, Select, Textarea } from "@/components/ui";
import { useBlogStudio } from "@/components/blog/studio/BlogStudioProvider";
import { BLOG_SEARCH_INTENTS, BLOG_TONES } from "@/components/blog/studio/types";
import { fetchAdminBlogPostTypes, type BlogPostType } from "@/lib/blog-api";
import { cn } from "@/lib/cn";
import type { WorkspaceTab } from "@/lib/blog-workspace";

type Props = {
  onNavigate: (tab: WorkspaceTab) => void;
};

export function BlogPlanWorkspace({ onNavigate }: Props) {
  const studio = useBlogStudio();
  const [briefOpen, setBriefOpen] = useState(true);
  const [postTypes, setPostTypes] = useState<BlogPostType[]>([]);

  const brief = studio.brief;
  const outline = studio.outline;

  useEffect(() => {
    void (async () => {
      try {
        const rows = await fetchAdminBlogPostTypes({ includeArchived: true });
        setPostTypes(rows);
      } catch {
        setPostTypes([]);
      }
    })();
  }, []);

  const activeTypes = postTypes.filter((t) => t.is_active !== false);
  const selected = postTypes.find((t) => t.id === studio.postTypeId);
  const typeOptions =
    selected && selected.is_active === false
      ? [selected, ...activeTypes.filter((t) => t.id !== selected.id)]
      : activeTypes;

  return (
    <div className="flex min-h-0 flex-1">
      {/* Left: Content Brief */}
      <aside
        className={cn(
          "border-r border-border bg-card transition-all duration-200 overflow-y-auto",
          briefOpen ? "w-72 shrink-0" : "w-0 overflow-hidden",
        )}
      >
        <div className="p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Content Brief</h2>
          </div>
          <Input
            label="Topic"
            value={brief.topic ?? ""}
            onChange={(e) => studio.setBrief({ ...brief, topic: e.target.value })}
          />
          <Input
            label="Primary keyword"
            value={brief.primary_keyword ?? ""}
            onChange={(e) => {
              studio.setBrief({ ...brief, primary_keyword: e.target.value });
              studio.patch({ focusKeyword: e.target.value });
            }}
          />
          <Textarea
            label="Secondary keywords"
            rows={2}
            value={(brief.secondary_keywords ?? []).join(", ")}
            onChange={(e) =>
              studio.setBrief({
                ...brief,
                secondary_keywords: e.target.value
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean),
              })
            }
          />
          <Input
            label="Target audience"
            value={brief.target_audience ?? ""}
            onChange={(e) => studio.setBrief({ ...brief, target_audience: e.target.value })}
          />
          <Select
            label="Search intent"
            value={brief.search_intent ?? "Informational"}
            onChange={(e) => studio.setBrief({ ...brief, search_intent: e.target.value })}
          >
            {BLOG_SEARCH_INTENTS.map((i) => (
              <option key={i} value={i}>{i}</option>
            ))}
          </Select>
          <Textarea
            label="Article objective"
            rows={2}
            value={brief.article_objective ?? ""}
            onChange={(e) => studio.setBrief({ ...brief, article_objective: e.target.value })}
          />
          <Select
            label="Post type"
            value={studio.postTypeId || ""}
            onChange={(e) => {
              const id = e.target.value;
              const row = postTypes.find((t) => t.id === id);
              studio.patch({ postTypeId: id, dirty: true });
              studio.setBrief({
                ...brief,
                post_type_id: id || undefined,
                post_type_key: row?.key || undefined,
                post_type_name: row?.name || undefined,
                // Keep legacy content_type as display mirror only (not authority).
                content_type: row?.name || brief.content_type,
              });
            }}
          >
            <option value="">Select post type</option>
            {typeOptions.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
                {t.is_active === false ? " (Archived)" : ""}
              </option>
            ))}
          </Select>
          {selected?.description ? (
            <p className="text-xs text-muted-foreground">{selected.description}</p>
          ) : null}
          <Select
            label="Tone"
            value={brief.tone ?? "Professional"}
            onChange={(e) => studio.setBrief({ ...brief, tone: e.target.value })}
          >
            {BLOG_TONES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </Select>
        </div>
      </aside>

      {/* Collapse toggle */}
      <button
        type="button"
        className="shrink-0 w-5 self-stretch flex items-center justify-center bg-surface/50 hover:bg-surface border-r border-border text-muted-foreground"
        onClick={() => setBriefOpen((v) => !v)}
        title={briefOpen ? "Collapse brief" : "Expand brief"}
      >
        <svg className="h-3 w-3" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path d={briefOpen ? "M10 4L6 8l4 4" : "M6 4l4 4-4 4"} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {/* Main: Title + Outline */}
      <main className="flex-1 min-w-0 overflow-y-auto p-6 space-y-6">
        <div className="space-y-1">
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            Article title
          </label>
          <input
            className="w-full text-2xl font-bold bg-transparent border-b border-border focus:border-primary outline-none py-1 text-foreground placeholder:text-muted-foreground/50"
            placeholder="Enter a working title…"
            value={studio.title}
            onChange={(e) => {
              const title = e.target.value;
              studio.patch({ title, dirty: true });
              if (!brief.topic) studio.setBrief({ ...brief, topic: title });
            }}
          />
        </div>

        <Textarea
          label="Article summary / excerpt"
          rows={3}
          value={studio.excerpt}
          onChange={(e) => studio.patch({ excerpt: e.target.value, dirty: true })}
        />

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Outline</h3>
          </div>

          {outline.sections.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No outline yet. Fill in the brief and use AI Assistant to generate one, or add sections manually.
            </p>
          ) : (
            <ol className="space-y-2">
              {outline.sections.map((sec, i) => (
                <li key={sec.id} className="flex items-start gap-2">
                  <span className="mt-1 shrink-0 text-xs text-muted-foreground w-5">{i + 1}.</span>
                  <input
                    className="flex-1 bg-transparent border-b border-border/50 focus:border-primary outline-none text-sm py-0.5 text-foreground"
                    value={sec.heading}
                    onChange={(e) => {
                      studio.setOutline({
                        ...outline,
                        sections: outline.sections.map((s) =>
                          s.id === sec.id ? { ...s, heading: e.target.value } : s,
                        ),
                      });
                    }}
                  />
                </li>
              ))}
            </ol>
          )}

          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              const id = `sec-${Date.now().toString(36)}`;
              studio.setOutline({
                ...outline,
                sections: [...outline.sections, { id, heading: "New section" }],
              });
            }}
          >
            + Add section
          </Button>
        </div>

        <div className="space-y-3">
          <Textarea
            label="Introduction purpose"
            rows={2}
            value={outline.introduction_purpose ?? ""}
            onChange={(e) =>
              studio.setOutline({ ...outline, introduction_purpose: e.target.value })
            }
          />
          <Textarea
            label="Conclusion direction"
            rows={2}
            value={outline.conclusion_direction ?? ""}
            onChange={(e) =>
              studio.setOutline({ ...outline, conclusion_direction: e.target.value })
            }
          />
        </div>

        <div className="flex items-center gap-3 pt-2">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={outline.approved ?? false}
              onChange={(e) => studio.setOutline({ ...outline, approved: e.target.checked })}
              className="rounded"
            />
            Outline approved
          </label>
        </div>

        <div className="pt-4 border-t border-border">
          <Button onClick={() => onNavigate("write")} className="gap-2">
            Continue to Write →
          </Button>
        </div>
      </main>
    </div>
  );
}
