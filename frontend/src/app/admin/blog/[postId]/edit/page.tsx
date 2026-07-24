"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { BlogAIAssist } from "@/components/blog/BlogAIAssist";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Input,
  Select,
  Switch,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  checkBlogSlug,
  deleteAdminBlogPost,
  fetchAdminBlogAuthors,
  fetchAdminBlogCategories,
  fetchAdminBlogPost,
  fetchAdminBlogTags,
  publishAdminBlogPost,
  unpublishAdminBlogPost,
  updateAdminBlogPost,
  type BlogAuthor,
  type BlogCategory,
  type BlogPost,
  type BlogTag,
} from "@/lib/blog-api";

export default function AdminBlogEditPage() {
  const { postId } = useParams<{ postId: string }>();
  const router = useRouter();
  const toast = useToast();
  const [post, setPost] = useState<BlogPost | null>(null);
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [body, setBody] = useState("");
  const [coverUrl, setCoverUrl] = useState("");
  const [ogImage, setOgImage] = useState("");
  const [canonical, setCanonical] = useState("");
  const [seoTitle, setSeoTitle] = useState("");
  const [seoDescription, setSeoDescription] = useState("");
  const [adminNotes, setAdminNotes] = useState("");
  const [featured, setFeatured] = useState(false);
  const [categoryId, setCategoryId] = useState("");
  const [authorId, setAuthorId] = useState("");
  const [tagIds, setTagIds] = useState<string[]>([]);
  const [categories, setCategories] = useState<BlogCategory[]>([]);
  const [tags, setTags] = useState<BlogTag[]>([]);
  const [authors, setAuthors] = useState<BlogAuthor[]>([]);
  const [slugOk, setSlugOk] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [scheduledAt, setScheduledAt] = useState("");
  const [preview, setPreview] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [p, c, t, a] = await Promise.all([
        fetchAdminBlogPost(postId),
        fetchAdminBlogCategories(),
        fetchAdminBlogTags(),
        fetchAdminBlogAuthors(),
      ]);
      setPost(p);
      setTitle(p.title);
      setSlug(p.slug);
      setExcerpt(p.excerpt || "");
      setBody(p.body);
      setCoverUrl(p.cover_url || "");
      setOgImage(p.og_image_url || "");
      setCanonical(p.canonical_url || "");
      setSeoTitle(p.seo_title || "");
      setSeoDescription(p.seo_description || "");
      setAdminNotes(p.admin_notes || "");
      setFeatured(p.is_featured);
      setCategoryId(p.category?.id || "");
      setAuthorId(p.author?.id || "");
      setTagIds((p.tags || []).map((x) => x.id));
      setScheduledAt(
        p.scheduled_at
          ? new Date(p.scheduled_at).toISOString().slice(0, 16)
          : "",
      );
      setCategories(c);
      setTags(t);
      setAuthors(a);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load");
    }
  }, [postId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate editor
    void load();
  }, [load]);

  useEffect(() => {
    if (!slug.trim() || !post) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reset slug check
      setSlugOk(null);
      return;
    }
    const t = setTimeout(() => {
      void checkBlogSlug(slug, post.id)
        .then((r) => setSlugOk(r.available))
        .catch(() => setSlugOk(null));
    }, 300);
    return () => clearTimeout(t);
  }, [slug, post]);

  async function save() {
    setBusy(true);
    try {
      const updated = await updateAdminBlogPost(postId, {
        title,
        slug,
        excerpt,
        body,
        cover_url: coverUrl || null,
        og_image_url: ogImage || null,
        canonical_url: canonical || null,
        seo_title: seoTitle || null,
        seo_description: seoDescription || null,
        admin_notes: adminNotes || null,
        is_featured: featured,
        category_id: categoryId || null,
        author_id: authorId || null,
        tag_ids: tagIds,
        scheduled_at: scheduledAt
          ? new Date(scheduledAt).toISOString()
          : null,
      });
      setPost(updated);
      toast.push({ tone: "success", title: "Saved" });
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Save failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function act(kind: "publish" | "unpublish" | "archive") {
    setBusy(true);
    try {
      if (kind === "publish") await publishAdminBlogPost(postId);
      else if (kind === "unpublish") await unpublishAdminBlogPost(postId);
      else {
        await deleteAdminBlogPost(postId);
        toast.push({ tone: "success", title: "Archived" });
        router.push("/admin/blog");
        return;
      }
      toast.push({ tone: "success", title: "Updated" });
      await load();
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Action failed",
      });
    } finally {
      setBusy(false);
    }
  }

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

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Blog"
      title={title || "Edit post"}
      description="Edit content, SEO, and publish state."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={post.status === "published" ? "success" : "neutral"}>
            {post.status}
          </Badge>
          <Link
            href={`/blog/${post.slug}`}
            target="_blank"
            className="text-sm font-semibold text-primary"
          >
            Public view
          </Link>
          <Link href="/admin/blog" className="text-sm font-semibold text-primary">
            Back
          </Link>
        </div>
      }
    >
      <div className="mx-auto max-w-3xl space-y-4">
        <BlogAIAssist
          blogPostId={postId}
          values={{
            title,
            excerpt,
            body,
            categoryName:
              categories.find((c) => c.id === categoryId)?.name || "",
            existingTags: tags
              .filter((t) => tagIds.includes(t.id))
              .map((t) => t.name)
              .join(", "),
            existingSlug: slug,
            existingSeoTitle: seoTitle,
            existingSeoDescription: seoDescription,
          }}
          catalogTags={tags}
          onApplyTitle={setTitle}
          onApplyOutline={(outline) => {
            setBody((prev) =>
              prev.trim()
                ? `${prev.trim()}\n\n${outline}`
                : outline,
            );
          }}
          onApplyExcerpt={setExcerpt}
          onApplySeo={(meta) => {
            const overwriteSeo =
              !seoTitle.trim() && !seoDescription.trim()
                ? true
                : window.confirm(
                    "Replace existing SEO title/description with the AI draft?",
                  );
            if (overwriteSeo) {
              setSeoTitle(meta.seo_title);
              setSeoDescription(meta.seo_description);
            }
            if (
              !slug.trim() ||
              window.confirm(
                "Replace the current slug with the AI suggestion?",
              )
            ) {
              setSlug(meta.suggested_slug);
            }
          }}
          onApplyTags={(ids) =>
            setTagIds((prev) => Array.from(new Set([...prev, ...ids])))
          }
        />
        <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Input
          label="Slug"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          hint={
            slugOk === null
              ? undefined
              : slugOk
                ? "Slug available"
                : "Slug already taken"
          }
        />
        <Textarea
          label="Excerpt"
          value={excerpt}
          onChange={(e) => setExcerpt(e.target.value)}
          rows={2}
        />
        <Textarea
          label="Body (markdown)"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={16}
        />
        <Button
          size="sm"
          variant="secondary"
          onClick={() => setPreview((v) => !v)}
        >
          {preview ? "Hide preview" : "Preview HTML"}
        </Button>
        {preview ? (
          <div
            className="prose prose-sm dark:prose-invert max-w-none rounded-[var(--radius-md)] border border-border bg-surface-muted p-4"
            dangerouslySetInnerHTML={{ __html: post.body_html }}
          />
        ) : null}
        <Input
          label="Cover image URL"
          value={coverUrl}
          onChange={(e) => setCoverUrl(e.target.value)}
        />
        <Input
          label="Open Graph image URL"
          value={ogImage}
          onChange={(e) => setOgImage(e.target.value)}
        />
        <Input
          label="Canonical URL"
          value={canonical}
          onChange={(e) => setCanonical(e.target.value)}
        />
        <Select
          label="Category"
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
        >
          <option value="">None</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <Select
          label="Author"
          value={authorId}
          onChange={(e) => setAuthorId(e.target.value)}
        >
          <option value="">None</option>
          {authors.map((a) => (
            <option key={a.id} value={a.id}>
              {a.display_name}
            </option>
          ))}
        </Select>
        <div>
          <p className="mb-2 text-sm font-semibold">Tags</p>
          <div className="flex flex-wrap gap-2">
            {tags.map((t) => {
              const on = tagIds.includes(t.id);
              return (
                <button
                  key={t.id}
                  type="button"
                  className={
                    on
                      ? "rounded-full bg-primary px-3 py-1 text-xs font-bold text-primary-foreground"
                      : "rounded-full border border-border px-3 py-1 text-xs font-semibold"
                  }
                  onClick={() =>
                    setTagIds((prev) =>
                      on ? prev.filter((x) => x !== t.id) : [...prev, t.id],
                    )
                  }
                >
                  {t.name}
                </button>
              );
            })}
          </div>
        </div>
        <Input
          label="SEO title"
          value={seoTitle}
          onChange={(e) => setSeoTitle(e.target.value)}
        />
        <Textarea
          label="SEO description"
          value={seoDescription}
          onChange={(e) => setSeoDescription(e.target.value)}
          rows={2}
        />
        <Textarea
          label="Admin notes (private)"
          value={adminNotes}
          onChange={(e) => setAdminNotes(e.target.value)}
          rows={2}
          hint="Never shown on the public blog."
        />
        <Input
          label="Schedule publish"
          type="datetime-local"
          value={scheduledAt}
          onChange={(e) => setScheduledAt(e.target.value)}
        />
        <Switch
          checked={featured}
          onCheckedChange={setFeatured}
          label="Featured on blog home"
        />
        <div className="flex flex-wrap gap-2 pt-2">
          <Button disabled={busy} onClick={() => void save()}>
            Save
          </Button>
          {post.status !== "published" ? (
            <Button
              disabled={busy}
              variant="secondary"
              onClick={() => void act("publish")}
            >
              Publish now
            </Button>
          ) : (
            <Button
              disabled={busy}
              variant="secondary"
              onClick={() => void act("unpublish")}
            >
              Unpublish
            </Button>
          )}
          <Button
            disabled={busy}
            variant="danger"
            onClick={() => void act("archive")}
          >
            Archive
          </Button>
        </div>
      </div>
    </DashboardShell>
  );
}
