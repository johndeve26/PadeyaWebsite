"use client";
// BlogPublishWorkspace — Publish tab: settings + readiness checklist + publish action

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button, Badge, Input, Select, Switch, Textarea } from "@/components/ui";
import { useBlogStudio } from "@/components/blog/studio/BlogStudioProvider";
import { useBlogStudioAutosave } from "@/components/blog/studio/useBlogStudioAutosave";
import {
  fetchAdminBlogCategories,
  fetchAdminBlogAuthors,
  publishAdminBlogPost,
  unpublishAdminBlogPost,
  type BlogCategory,
  type BlogAuthor,
} from "@/lib/blog-api";
import { computeChecklist } from "@/lib/blog-workspace";
import { ApiError } from "@/lib/api";
import { useToast } from "@/components/ui";
import { clearLocalStudioDraft } from "@/components/blog/studio/useBlogStudioAutosave";
import { cn } from "@/lib/cn";

export function BlogPublishWorkspace() {
  const studio = useBlogStudio();
  const toast = useToast();
  const router = useRouter();
  const { saveNow } = useBlogStudioAutosave({ enabled: true });
  const [categories, setCategories] = useState<BlogCategory[]>([]);
  const [authors, setAuthors] = useState<BlogAuthor[]>([]);
  const [busy, setBusy] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const [c, a] = await Promise.all([fetchAdminBlogCategories(), fetchAdminBlogAuthors()]);
        setCategories(c);
        setAuthors(a);
      } catch {
        /* empty catalogs */
      }
    })();
  }, []);

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

  const allReady = checklist.every((item) => item.ok);
  const contentItems = checklist.filter((item) => ["title", "h2", "image_alt"].includes(item.id));
  const seoItems = checklist.filter((item) => ["meta_title", "meta_desc", "slug", "keyword_title"].includes(item.id));

  async function handlePublish() {
    setBusy(true);
    setConfirmOpen(false);
    try {
      await saveNow();
      if (!studio.postId) {
        toast.push({ tone: "danger", title: "Save a draft before publishing" });
        return;
      }
      const post = await publishAdminBlogPost(studio.postId);
      studio.patch({ status: post.status, dirty: false });
      clearLocalStudioDraft();
      toast.push({ tone: "success", title: "Published!" });
    } catch (e) {
      toast.push({ tone: "danger", title: e instanceof ApiError ? e.message : "Publish failed" });
    } finally {
      setBusy(false);
    }
  }

  async function handleUnpublish() {
    if (!studio.postId) return;
    setBusy(true);
    try {
      const post = await unpublishAdminBlogPost(studio.postId);
      studio.patch({ status: post.status });
      toast.push({ tone: "success", title: "Unpublished" });
    } catch (e) {
      toast.push({ tone: "danger", title: e instanceof ApiError ? e.message : "Unpublish failed" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left: Publish settings */}
        <div className="space-y-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Publish settings
          </h2>
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium">Status</span>
            <Badge tone={studio.status === "published" ? "success" : "neutral"}>
              {studio.status}
            </Badge>
          </div>
          <Select
            label="Category"
            value={studio.categoryId}
            onChange={(e) => studio.patch({ categoryId: e.target.value, dirty: true })}
          >
            <option value="">No category</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </Select>
          <Select
            label="Author"
            value={studio.authorId}
            onChange={(e) => studio.patch({ authorId: e.target.value, dirty: true })}
          >
            <option value="">No author</option>
            {authors.map((a) => (
              <option key={a.id} value={a.id}>{a.display_name}</option>
            ))}
          </Select>
          <Input
            label="Featured image URL"
            value={studio.coverUrl}
            onChange={(e) => studio.patch({ coverUrl: e.target.value, dirty: true })}
            placeholder="https://…"
          />
          <Input
            label="Schedule publication"
            type="datetime-local"
            value={studio.scheduledAt}
            onChange={(e) => studio.patch({ scheduledAt: e.target.value, dirty: true })}
          />
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Featured</span>
            <Switch
              checked={studio.featured}
              onCheckedChange={(v) => studio.patch({ featured: v, dirty: true })}
            />
          </div>
          <Textarea
            label="Revision note"
            rows={2}
            value={studio.adminNotes}
            onChange={(e) => studio.patch({ adminNotes: e.target.value, dirty: true })}
            placeholder="Optional note about this revision…"
          />
        </div>

        {/* Right: Readiness */}
        <div className="space-y-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Readiness checklist
          </h2>

          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Content</p>
            <ul className="rounded-lg border border-border bg-card divide-y divide-border px-4">
              {contentItems.map((item) => (
                <li key={item.id} className="flex items-center gap-2 py-2">
                  <span className={cn("h-3 w-3 rounded-full", item.ok ? "bg-success" : "bg-amber-400")} />
                  <span className="text-sm">{item.label}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">SEO</p>
            <ul className="rounded-lg border border-border bg-card divide-y divide-border px-4">
              {seoItems.map((item) => (
                <li key={item.id} className="flex items-center gap-2 py-2">
                  <span className={cn("h-3 w-3 rounded-full", item.ok ? "bg-success" : "bg-amber-400")} />
                  <span className="text-sm">{item.label}</span>
                </li>
              ))}
            </ul>
          </div>

          {!allReady ? (
            <p className="text-xs text-amber-600">
              Some checklist items are incomplete. You can still publish, but it is recommended to fix them first.
            </p>
          ) : (
            <p className="text-xs text-success">All checks passed.</p>
          )}

          <div className="pt-4 space-y-3 border-t border-border">
            {studio.postId && studio.slug ? (
              <Link
                href={`/blog/${studio.slug}`}
                target="_blank"
                className="block text-sm text-primary hover:underline"
              >
                Preview article →
              </Link>
            ) : null}

            {studio.status !== "published" ? (
              <>
                {confirmOpen ? (
                  <div className="rounded-lg border border-border bg-surface p-4 space-y-3">
                    <p className="text-sm font-semibold">
                      Publish &ldquo;{studio.title || "Untitled"}&rdquo;?
                    </p>
                    <p className="text-xs text-muted-foreground">
                      This will make the article publicly visible.
                    </p>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => void handlePublish()} disabled={busy}>
                        {busy ? "Publishing…" : "Yes, publish"}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setConfirmOpen(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button
                    className="w-full"
                    onClick={() => setConfirmOpen(true)}
                    disabled={busy}
                  >
                    Publish now
                  </Button>
                )}
              </>
            ) : (
              <Button
                variant="secondary"
                className="w-full"
                onClick={() => void handleUnpublish()}
                disabled={busy}
              >
                Unpublish
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
