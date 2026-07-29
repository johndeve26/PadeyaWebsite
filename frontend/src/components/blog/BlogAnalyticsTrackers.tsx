"use client";

import { useEffect, useRef } from "react";

import {
  trackBlogIndexView,
  trackBlogHubView,
  trackBlogPostView,
  trackBlogScrollMilestone,
} from "@/lib/analytics";

/** Index / hub page mount tracker (deduped). */
export function BlogIndexViewTracker({
  kind = "index",
  slug,
}: {
  kind?: "index" | "category" | "tag" | "author";
  slug?: string;
}) {
  useEffect(() => {
    if (kind === "index") trackBlogIndexView();
    else if (slug) trackBlogHubView(kind, { slug });
  }, [kind, slug]);
  return null;
}

/** Article view + scroll milestones (25/50/75/100). */
export function BlogPostViewTracker({
  postId,
  slug,
  categorySlug,
}: {
  postId: string;
  slug: string;
  categorySlug?: string | null;
}) {
  const fired = useRef<Set<number>>(new Set());

  useEffect(() => {
    trackBlogPostView({ postId, slug, categorySlug });
  }, [postId, slug, categorySlug]);

  useEffect(() => {
    const milestones = [25, 50, 75, 100] as const;
    const onScroll = () => {
      const doc = document.documentElement;
      const scrollTop = window.scrollY || doc.scrollTop;
      const height = doc.scrollHeight - window.innerHeight;
      if (height <= 0) return;
      const pct = Math.min(100, Math.round((scrollTop / height) * 100));
      for (const m of milestones) {
        if (pct >= m && !fired.current.has(m)) {
          fired.current.add(m);
          trackBlogScrollMilestone({ postId, slug, milestone: m });
        }
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, [postId, slug]);

  return null;
}
