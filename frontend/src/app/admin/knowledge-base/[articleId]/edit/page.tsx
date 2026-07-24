"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

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
  archiveAdminHelpArticle,
  fetchAdminHelpArticle,
  fetchAdminHelpCategories,
  publishAdminHelpArticle,
  updateAdminHelpArticle,
  type HelpArticle,
  type HelpCategory,
} from "@/lib/knowledge-base/api";

const CONTENT_TYPES = [
  "text",
  "how_to",
  "video",
  "faq",
  "troubleshooting",
  "policy",
  "update",
];
const AUDIENCES = ["fan", "host", "admin", "ambassador", "sponsor", "visitor"];

export default function AdminKnowledgeBaseEditPage() {
  const { articleId } = useParams<{ articleId: string }>();
  const router = useRouter();
  const toast = useToast();
  const [article, setArticle] = useState<HelpArticle | null>(null);
  const [categories, setCategories] = useState<HelpCategory[]>([]);
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [body, setBody] = useState("");
  const [contentType, setContentType] = useState("text");
  const [difficulty, setDifficulty] = useState("beginner");
  const [audiences, setAudiences] = useState<string[]>(["visitor"]);
  const [categoryId, setCategoryId] = useState("");
  const [tagSlugs, setTagSlugs] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [coverUrl, setCoverUrl] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [featured, setFeatured] = useState(false);
  const [seoTitle, setSeoTitle] = useState("");
  const [seoDescription, setSeoDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [a, cats] = await Promise.all([
        fetchAdminHelpArticle(articleId),
        fetchAdminHelpCategories(),
      ]);
      setArticle(a);
      setTitle(a.title);
      setSlug(a.slug);
      setExcerpt(a.excerpt || "");
      setBody(a.body || "");
      setContentType(a.content_type || "text");
      setDifficulty(a.difficulty || "beginner");
      setAudiences(a.audiences?.length ? a.audiences : ["visitor"]);
      setCategoryId(a.category?.id || "");
      setTagSlugs((a.tags || []).map((t) => t.slug).join(", "));
      setVideoUrl(a.video_url || "");
      setCoverUrl(a.cover_url || "");
      setScheduledAt(a.scheduled_at || "");
      setFeatured(a.is_featured);
      setSeoTitle(a.seo_title || "");
      setSeoDescription(a.seo_description || "");
      setCategories(cats);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load");
    }
  }, [articleId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate editor
    void load();
  }, [load]);

  async function save() {
    setBusy(true);
    try {
      const updated = await updateAdminHelpArticle(articleId, {
        title,
        slug,
        excerpt: excerpt || null,
        body,
        content_type: contentType,
        difficulty,
        audiences,
        category_id: categoryId || null,
        tag_slugs: tagSlugs
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        video_url: videoUrl || null,
        cover_url: coverUrl || null,
        scheduled_at: scheduledAt || null,
        status: scheduledAt ? "scheduled" : undefined,
        is_featured: featured,
        seo_title: seoTitle || null,
        seo_description: seoDescription || null,
      });
      setArticle(updated);
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

  async function act(kind: "publish" | "archive") {
    setBusy(true);
    try {
      if (kind === "publish") {
        await publishAdminHelpArticle(articleId);
        toast.push({ tone: "success", title: "Published" });
        await load();
      } else {
        await archiveAdminHelpArticle(articleId);
        toast.push({ tone: "success", title: "Archived" });
        router.push("/admin/knowledge-base");
      }
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Action failed",
      });
    } finally {
      setBusy(false);
    }
  }

  function toggleAudience(code: string) {
    setAudiences((prev) =>
      prev.includes(code) ? prev.filter((a) => a !== code) : [...prev, code],
    );
  }

  if (error) {
    return (
      <DashboardShell tone="soft" title="Edit article">
        <Alert tone="danger">{error}</Alert>
      </DashboardShell>
    );
  }

  if (!article) {
    return (
      <DashboardShell tone="soft" title="Edit article">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Knowledge Base"
      title={title || "Edit article"}
      description="Edit help content, video, SEO, and publish state."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            tone={
              article.status === "published"
                ? "success"
                : article.status === "archived"
                  ? "neutral"
                  : "warning"
            }
          >
            {article.status}
          </Badge>
          {article.status === "published" ? (
            <Link
              href={`/help/articles/${article.slug}`}
              target="_blank"
              className="text-sm font-semibold text-primary-text"
            >
              Public view
            </Link>
          ) : null}
          <Link href="/admin/knowledge-base">
            <Button size="sm" variant="ghost">
              Back
            </Button>
          </Link>
        </div>
      }
    >
      <div className="mx-auto max-w-3xl space-y-5">
        <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Input label="Slug" value={slug} onChange={(e) => setSlug(e.target.value)} />
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
        <div className="grid gap-4 sm:grid-cols-2">
          <Select
            label="Content type"
            value={contentType}
            onChange={(e) => setContentType(e.target.value)}
          >
            {CONTENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
          <Select
            label="Difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
          >
            <option value="beginner">beginner</option>
            <option value="intermediate">intermediate</option>
            <option value="advanced">advanced</option>
          </Select>
        </div>
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
        <Input
          label="Tags (comma-separated slugs)"
          value={tagSlugs}
          onChange={(e) => setTagSlugs(e.target.value)}
        />
        <Input
          label="Video URL"
          value={videoUrl}
          onChange={(e) => setVideoUrl(e.target.value)}
        />
        <Input
          label="Cover image URL"
          value={coverUrl}
          onChange={(e) => setCoverUrl(e.target.value)}
        />
        <Input
          label="Schedule publish (ISO datetime)"
          value={scheduledAt}
          onChange={(e) => setScheduledAt(e.target.value)}
          placeholder="2026-08-01T10:00:00Z"
        />
        <fieldset>
          <legend className="mb-2 text-sm font-semibold text-heading">
            Audiences
          </legend>
          <div className="flex flex-wrap gap-3">
            {AUDIENCES.map((a) => (
              <label key={a} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={audiences.includes(a)}
                  onChange={() => toggleAudience(a)}
                />
                {a}
              </label>
            ))}
          </div>
        </fieldset>
        <Switch
          checked={featured}
          onCheckedChange={setFeatured}
          label="Featured"
        />
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
        <div className="flex flex-wrap gap-2 pt-2">
          <Button disabled={busy} onClick={() => void save()}>
            Save
          </Button>
          {article.status !== "published" ? (
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => void act("publish")}
            >
              Publish
            </Button>
          ) : (
            <>
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() =>
                  void (async () => {
                    setBusy(true);
                    try {
                      await updateAdminHelpArticle(articleId, {
                        status: "draft",
                      });
                      toast.push({ tone: "success", title: "Unpublished" });
                      await load();
                    } catch (e) {
                      toast.push({
                        tone: "danger",
                        title:
                          e instanceof ApiError ? e.message : "Unpublish failed",
                      });
                    } finally {
                      setBusy(false);
                    }
                  })()
                }
              >
                Unpublish
              </Button>
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => void act("archive")}
              >
                Archive
              </Button>
            </>
          )}
        </div>
      </div>
    </DashboardShell>
  );
}
