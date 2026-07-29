"use client";
// BlogWorkspaceHeader — sticky workspace header with tabs and actions

import Link from "next/link";
import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui";
import { useBlogStudio } from "@/components/blog/studio/BlogStudioProvider";
import { cn } from "@/lib/cn";
import type { WorkspaceTab } from "@/lib/blog-workspace";

const TABS: { id: WorkspaceTab; label: string }[] = [
  { id: "plan", label: "Plan" },
  { id: "write", label: "Write" },
  { id: "design", label: "Design" },
  { id: "seo", label: "SEO & Social" },
  { id: "review", label: "Review" },
  { id: "publish", label: "Publish" },
];

type Props = {
  activeTab: WorkspaceTab;
  onTabChange: (tab: WorkspaceTab) => void;
  onAiAssistant: () => void;
  onPublish: () => void;
};

export function BlogWorkspaceHeader({ activeTab, onTabChange, onAiAssistant, onPublish }: Props) {
  const studio = useBlogStudio();
  const [editingTitle, setEditingTitle] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingTitle) titleRef.current?.focus();
  }, [editingTitle]);

  const autosaveEl = (() => {
    if (studio.autosaveStatus === "saving")
      return <span className="text-xs text-muted-foreground">Saving…</span>;
    if (studio.autosaveStatus === "saved")
      return (
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <svg className="h-3 w-3 text-success" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 1 1 1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0z" />
          </svg>
          Saved
        </span>
      );
    if (studio.autosaveStatus === "failed")
      return <span className="text-xs text-danger">Save failed</span>;
    return null;
  })();

  return (
    <header className="sticky top-[var(--header-height,4rem)] z-30 bg-card border-b border-border">
      <div className="flex items-center gap-3 px-4 py-2 min-h-[3rem]">
        {/* Left: back + title */}
        <div className="flex items-center gap-2 min-w-0 shrink">
          <Link
            href="/admin/blog"
            className="shrink-0 text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
          >
            <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M10 12L6 8l4-4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Blog
          </Link>
          <span className="text-muted-foreground/40 shrink-0">/</span>
          {editingTitle ? (
            <input
              ref={titleRef}
              className="min-w-0 flex-1 truncate bg-transparent text-sm font-semibold text-foreground outline-none border-b border-primary"
              value={studio.title}
              placeholder="Untitled post"
              onChange={(e) => studio.patch({ title: e.target.value, dirty: true })}
              onBlur={() => setEditingTitle(false)}
              onKeyDown={(e) => { if (e.key === "Enter") setEditingTitle(false); }}
            />
          ) : (
            <button
              type="button"
              className="min-w-0 truncate text-sm font-semibold text-foreground hover:text-primary text-left"
              onClick={() => setEditingTitle(true)}
              title="Click to edit title"
            >
              {studio.title || <span className="text-muted-foreground italic">Untitled post</span>}
            </button>
          )}
        </div>

        {/* Center: tabs */}
        <nav
          className="hidden md:flex flex-1 justify-center overflow-x-auto scrollbar-none gap-1 px-2"
          aria-label="Workspace tabs"
        >
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => onTabChange(tab.id)}
              className={cn(
                "shrink-0 py-2 px-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors",
                activeTab === tab.id
                  ? "text-primary border-primary"
                  : "text-muted-foreground border-transparent hover:text-foreground",
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Right: status + actions */}
        <div className="flex shrink-0 items-center gap-2">
          {autosaveEl}
          <Button size="sm" variant="ghost" onClick={onAiAssistant}>
            AI Assistant
          </Button>
          <Link
            href={studio.postId && studio.slug ? `/blog/${studio.slug}` : "#"}
            target="_blank"
            className="inline-flex items-center rounded-[var(--radius-md)] border border-border bg-surface px-3 py-1.5 text-sm font-medium hover:bg-surface-muted transition-colors"
          >
            Preview
          </Link>
          <Button size="sm" onClick={onPublish}>
            Review &amp; Publish
          </Button>
        </div>
      </div>

      {/* Mobile tabs row */}
      <div className="flex md:hidden overflow-x-auto scrollbar-none gap-1 px-4 pb-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => onTabChange(tab.id)}
            className={cn(
              "shrink-0 py-1.5 px-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors",
              activeTab === tab.id
                ? "text-primary border-primary"
                : "text-muted-foreground border-transparent hover:text-foreground",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </header>
  );
}
