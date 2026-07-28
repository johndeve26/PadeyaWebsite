"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { BlogStudioPage } from "@/components/blog/studio/BlogStudioPage";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAdminBlogPost, type BlogPost } from "@/lib/blog-api";

export default function AdminBlogEditPage() {
  const { postId } = useParams<{ postId: string }>();
  const [post, setPost] = useState<BlogPost | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const p = await fetchAdminBlogPost(postId);
      setPost(p);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load");
    }
  }, [postId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate editor
    void load();
  }, [load]);

  if (error) {
    return (
      <DashboardShell tone="soft" title="Edit post">
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      </DashboardShell>
    );
  }

  if (!post) {
    return (
      <DashboardShell tone="soft" title="Edit post">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </DashboardShell>
    );
  }

  return <BlogStudioPage mode="edit" initialPost={post} />;
}
