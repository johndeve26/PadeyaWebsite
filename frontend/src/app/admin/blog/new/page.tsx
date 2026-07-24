"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BlogAIAssist } from "@/components/blog/BlogAIAssist";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
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
  createAdminBlogPost,
  fetchAdminBlogAuthors,
  fetchAdminBlogCategories,
  fetchAdminBlogTags,
  publishAdminBlogPost,
  type BlogAuthor,
  type BlogCategory,
  type BlogTag,
} from "@/lib/blog-api";

export default function AdminBlogNewPage() {
  const router = useRouter();
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [body, setBody] = useState(
    "## Headline\n\nWrite in markdown. Use ::cta{label=\"Explore events\"; href=\"/events\"} for CTAs.\n",
  );
  const [coverUrl, setCoverUrl] = useState("");
  const [seoTitle, setSeoTitle] = useState("");
  const [seoDescription, setSeoDescription] = useState("");
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
        /* empty */
      }
    })();
  }, []);

  useEffect(() => {
    if (!slug.trim()) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reset slug check
      setSlugOk(null);
      return;
    }
    const t = setTimeout(() => {
      void checkBlogSlug(slug)
        .then((r) => setSlugOk(r.available))
        .catch(() => setSlugOk(null));
    }, 300);
    return () => clearTimeout(t);
  }, [slug]);

  async function save(publish: boolean) {
    setBusy(true);
    try {
      const post = await createAdminBlogPost({
        title,
        slug: slug || undefined,
        excerpt,
        body,
        cover_url: coverUrl || null,
        seo_title: seoTitle || null,
        seo_description: seoDescription || null,
        is_featured: featured,
        category_id: categoryId || null,
        author_id: authorId || null,
        tag_ids: tagIds,
        scheduled_at: scheduledAt
          ? new Date(scheduledAt).toISOString()
          : null,
      });
      if (publish) await publishAdminBlogPost(post.id);
      toast.push({
        tone: "success",
        title: publish ? "Published" : "Draft saved",
      });
      router.push(`/admin/blog/${post.id}/edit`);
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Save failed",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Blog"
      title="New post"
      description="Markdown editor with SEO fields. Preview after save."
      actions={
        <Link href="/admin/blog" className="text-sm font-semibold text-primary">
          Back
        </Link>
      }
    >
      <div className="mx-auto max-w-3xl space-y-4">
        <BlogAIAssist
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
        <Input
          label="Title"
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
            if (!slug) {
              setSlug(
                e.target.value
                  .toLowerCase()
                  .replace(/[^a-z0-9]+/g, "-")
                  .replace(/^-|-$/g, ""),
              );
            }
          }}
        />
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
        <Alert tone="info" title="Editor tips">
          Headings (# ## ###), lists, quotes (&gt;), links, images
          ![alt](https://…), code fences, and embeds ::cta / ::event / ::host.
        </Alert>
        <Input
          label="Cover image URL"
          value={coverUrl}
          onChange={(e) => setCoverUrl(e.target.value)}
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
        <Input label="SEO title" value={seoTitle} onChange={(e) => setSeoTitle(e.target.value)} />
        <Textarea
          label="SEO description"
          value={seoDescription}
          onChange={(e) => setSeoDescription(e.target.value)}
          rows={2}
        />
        <Input
          label="Schedule publish (optional)"
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
          <Button
            disabled={busy}
            onClick={() => void save(true)}
          >
            Publish now
          </Button>
          <Button
            disabled={busy}
            variant="secondary"
            onClick={() => void save(false)}
          >
            Save draft
          </Button>
        </div>
      </div>
    </DashboardShell>
  );
}
