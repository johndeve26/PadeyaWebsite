"use client";
// BlogWorkspaceShell — orchestrates the 6-tab blog workspace
// Tabs: plan | write | design | seo | review | publish

import { useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BlogStudioProvider } from "@/components/blog/studio/BlogStudioProvider";
import { validateTab } from "@/lib/blog-workspace";
import type { WorkspaceTab } from "@/lib/blog-workspace";
import { BlogWorkspaceHeader } from "./BlogWorkspaceHeader";
import { BlogPlanWorkspace } from "./BlogPlanWorkspace";
import { BlogWriteWorkspace } from "./BlogWriteWorkspace";
import { BlogDesignWorkspace } from "./BlogDesignWorkspace";
import { BlogSeoWorkspace } from "./BlogSeoWorkspace";
import { BlogReviewWorkspace } from "./BlogReviewWorkspace";
import { BlogPublishWorkspace } from "./BlogPublishWorkspace";
import { BlogAiDrawer } from "./BlogAiDrawer";
import { WorkspaceDocumentProvider } from "./WorkspaceDocumentProvider";
import type { BlogPost } from "@/lib/blog-api";
import type { BlogContentBrief, BlogOutline, BlogFaqItem } from "@/components/blog/studio/types";
import { parseContentDocument, resolveContentMode } from "@/lib/blog-document";

type SeedProps = Partial<{
  postId: string | null;
  title: string;
  slug: string;
  excerpt: string;
  body: string;
  coverUrl: string;
  seoTitle: string;
  seoDescription: string;
  canonicalUrl: string;
  ogImageUrl: string;
  ogTitle: string;
  socialShareText: string;
  focusKeyword: string;
  secondaryKeywords: string[];
  featured: boolean;
  categoryId: string;
  authorId: string;
  tagIds: string[];
  scheduledAt: string;
  adminNotes: string;
  status: string;
  contentVersion: number;
  bodyHtml: string | null;
  brief: BlogContentBrief;
  outline: BlogOutline;
  faqs: BlogFaqItem[];
}>;

function buildSeed(post: BlogPost): SeedProps {
  const p = post as BlogPost & {
    content_version?: number;
    focus_keyword?: string | null;
    secondary_keywords?: string[] | null;
    social_share_text?: string | null;
    og_title?: string | null;
    studio_brief?: BlogContentBrief | null;
    studio_outline?: BlogOutline | null;
    faqs?: BlogFaqItem[] | null;
    content_document?: Record<string, unknown>;
    content_mode?: string;
    editor_mode?: string;
    hero_settings?: Record<string, unknown>;
  };
  return {
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
    brief: p.studio_brief || undefined,
    outline: p.studio_outline || undefined,
    faqs: p.faqs || undefined,
  };
}

function WorkspaceInner({
  initialTab,
}: {
  initialTab: WorkspaceTab;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = validateTab(searchParams.get("tab")) || initialTab;
  const [aiOpen, setAiOpen] = useState(false);

  const setTab = useCallback(
    (tab: WorkspaceTab) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("tab", tab);
      router.replace(`?${params.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  const handlePublishTab = useCallback(() => setTab("publish"), [setTab]);

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <BlogWorkspaceHeader
        activeTab={activeTab}
        onTabChange={setTab}
        onAiAssistant={() => setAiOpen((v) => !v)}
        onPublish={handlePublishTab}
      />

      <div className="flex flex-1 min-h-0 relative">
        <div
          id="blog-workspace-panel-plan"
          role="tabpanel"
          aria-labelledby="blog-workspace-tab-plan"
          hidden={activeTab !== "plan"}
          className={activeTab === "plan" ? "flex min-h-0 flex-1 w-full" : "hidden"}
        >
          <BlogPlanWorkspace onNavigate={setTab} />
        </div>
        <div
          id="blog-workspace-panel-write"
          role="tabpanel"
          aria-labelledby="blog-workspace-tab-write"
          hidden={activeTab !== "write"}
          className={activeTab === "write" ? "flex min-h-0 flex-1 w-full" : "hidden"}
        >
          <BlogWriteWorkspace onAiAssistant={() => setAiOpen(true)} />
        </div>
        <div
          id="blog-workspace-panel-design"
          role="tabpanel"
          aria-labelledby="blog-workspace-tab-design"
          hidden={activeTab !== "design"}
          className={activeTab === "design" ? "flex min-h-0 flex-1 w-full" : "hidden"}
        >
          <BlogDesignWorkspace />
        </div>
        <div
          id="blog-workspace-panel-seo"
          role="tabpanel"
          aria-labelledby="blog-workspace-tab-seo"
          hidden={activeTab !== "seo"}
          className={activeTab === "seo" ? "flex min-h-0 flex-1 w-full" : "hidden"}
        >
          <BlogSeoWorkspace />
        </div>
        <div
          id="blog-workspace-panel-review"
          role="tabpanel"
          aria-labelledby="blog-workspace-tab-review"
          hidden={activeTab !== "review"}
          className={activeTab === "review" ? "flex min-h-0 flex-1 w-full" : "hidden"}
        >
          <BlogReviewWorkspace onNavigate={setTab} />
        </div>
        <div
          id="blog-workspace-panel-publish"
          role="tabpanel"
          aria-labelledby="blog-workspace-tab-publish"
          hidden={activeTab !== "publish"}
          className={activeTab === "publish" ? "flex min-h-0 flex-1 w-full" : "hidden"}
        >
          <BlogPublishWorkspace />
        </div>
      </div>

      <BlogAiDrawer
        open={aiOpen}
        onClose={() => setAiOpen(false)}
        activeTab={activeTab}
      />
    </div>
  );
}

export function BlogWorkspaceShell({
  postId: _postId,
  initialPost,
  initialTab = "write",
}: {
  postId?: string | null;
  initialPost?: BlogPost | null;
  initialTab?: WorkspaceTab;
}) {
  const seed = initialPost ? buildSeed(initialPost) : undefined;

  return (
    <BlogStudioProvider initial={seed}>
      <WorkspaceDocumentProvider>
        <WorkspaceInner initialTab={initialTab} />
      </WorkspaceDocumentProvider>
    </BlogStudioProvider>
  );
}
