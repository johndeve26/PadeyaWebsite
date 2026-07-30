"use client";
// BlogWorkspaceHeader — sticky workspace header with tabs and actions

import Link from "next/link";
import { useState, useRef, useEffect, useCallback } from "react";
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

function tabPanelId(tab: WorkspaceTab) {
  return `blog-workspace-panel-${tab}`;
}

function tabButtonId(tab: WorkspaceTab) {
  return `blog-workspace-tab-${tab}`;
}

export function BlogWorkspaceHeader({ activeTab, onTabChange, onAiAssistant, onPublish }: Props) {
  const studio = useBlogStudio();
  const [editingTitle, setEditingTitle] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);
  const mobileTabsRef = useRef<HTMLDivElement>(null);
  const desktopTabsRef = useRef<HTMLDivElement>(null);
  const prefersReducedMotion = useRef(false);

  useEffect(() => {
    if (editingTitle) titleRef.current?.focus();
  }, [editingTitle]);

  useEffect(() => {
    prefersReducedMotion.current = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
  }, []);

  const scrollTabIntoView = useCallback((tab: WorkspaceTab) => {
    const id = tabButtonId(tab);
    const el =
      mobileTabsRef.current?.querySelector<HTMLElement>(`#${id}`) ??
      desktopTabsRef.current?.querySelector<HTMLElement>(`#${id}`);
    el?.scrollIntoView({
      block: "nearest",
      inline: "center",
      behavior: prefersReducedMotion.current ? "auto" : "smooth",
    });
  }, []);

  useEffect(() => {
    scrollTabIntoView(activeTab);
  }, [activeTab, scrollTabIntoView]);

  const onTabKeyDown = useCallback(
    (e: React.KeyboardEvent, current: WorkspaceTab) => {
      const idx = TABS.findIndex((t) => t.id === current);
      if (idx < 0) return;
      let next: WorkspaceTab | null = null;
      if (e.key === "ArrowRight") next = TABS[(idx + 1) % TABS.length]!.id;
      if (e.key === "ArrowLeft") next = TABS[(idx - 1 + TABS.length) % TABS.length]!.id;
      if (e.key === "Home") next = TABS[0]!.id;
      if (e.key === "End") next = TABS[TABS.length - 1]!.id;
      if (next) {
        e.preventDefault();
        onTabChange(next);
        requestAnimationFrame(() => {
          document.getElementById(tabButtonId(next!))?.focus();
        });
      }
    },
    [onTabChange],
  );

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
    if (studio.autosaveStatus === "conflict")
      return <span className="text-xs text-danger">Conflict</span>;
    return null;
  })();

  const renderTab = (tab: (typeof TABS)[number]) => (
    <button
      key={tab.id}
      id={tabButtonId(tab.id)}
      type="button"
      role="tab"
      aria-selected={activeTab === tab.id}
      aria-controls={tabPanelId(tab.id)}
      tabIndex={activeTab === tab.id ? 0 : -1}
      onClick={() => onTabChange(tab.id)}
      onKeyDown={(e) => onTabKeyDown(e, tab.id)}
      className={cn(
        "shrink-0 py-2 px-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2",
        activeTab === tab.id
          ? "text-primary border-primary"
          : "text-muted-foreground border-transparent hover:text-foreground",
      )}
    >
      {tab.label}
    </button>
  );

  return (
    <header className="z-30 shrink-0 border-b border-border bg-card dark:bg-surface-elevated">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2 md:min-h-[3rem]">
        <div className="flex min-w-0 w-full items-center gap-2 md:w-auto md:flex-1 md:max-w-[min(100%,28rem)]">
          <Link
            href="/admin/blog"
            className="flex shrink-0 items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M10 12L6 8l4-4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>Blog</span>
          </Link>
          <span className="shrink-0 text-muted-foreground/40">/</span>
          {editingTitle ? (
            <input
              ref={titleRef}
              className="min-w-0 flex-1 truncate border-b border-primary bg-transparent text-sm font-semibold text-foreground outline-none"
              value={studio.title}
              placeholder="Untitled post"
              onChange={(e) => studio.patch({ title: e.target.value, dirty: true })}
              onBlur={() => setEditingTitle(false)}
              onKeyDown={(e) => { if (e.key === "Enter") setEditingTitle(false); }}
            />
          ) : (
            <button
              type="button"
              className="min-w-0 flex-1 truncate text-left text-sm font-semibold text-foreground hover:text-primary"
              onClick={() => setEditingTitle(true)}
              title="Click to edit title"
            >
              {studio.title || <span className="italic text-muted-foreground">Untitled post</span>}
            </button>
          )}
        </div>

        <nav
          ref={desktopTabsRef}
          className="hidden md:flex flex-1 justify-center overflow-x-auto scrollbar-none gap-1 px-2"
          role="tablist"
          aria-label="Workspace tabs"
        >
          {TABS.map(renderTab)}
        </nav>

        <div className="flex w-full shrink-0 items-center justify-end gap-1.5 sm:gap-2 md:w-auto">
          {autosaveEl}
          <Button size="sm" variant="ghost" onClick={onAiAssistant} className="shrink-0 px-2 sm:px-3">
            <span className="sm:hidden">AI</span>
            <span className="hidden sm:inline">AI Assistant</span>
          </Button>
          <Link
            href={studio.postId && studio.slug ? `/blog/${studio.slug}` : "#"}
            target="_blank"
            className="hidden shrink-0 items-center rounded-[var(--radius-md)] border border-border bg-surface px-3 py-1.5 text-sm font-medium transition-colors hover:bg-surface-muted sm:inline-flex"
          >
            Preview
          </Link>
          <Button size="sm" onClick={onPublish} className="shrink-0">
            <span className="sm:hidden">Publish</span>
            <span className="hidden sm:inline">Review &amp; Publish</span>
          </Button>
        </div>
      </div>

      <div
        ref={mobileTabsRef}
        className="flex overflow-x-auto scrollbar-none gap-1 px-4 pb-1 md:hidden"
        role="tablist"
        aria-label="Workspace tabs"
      >
        {TABS.map(renderTab)}
      </div>
    </header>
  );
}
