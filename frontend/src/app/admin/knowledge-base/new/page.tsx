"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

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
  createAdminHelpArticle,
  fetchAdminHelpCategories,
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

export default function AdminKnowledgeBaseNewPage() {
  const router = useRouter();
  const toast = useToast();
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
  const [featured, setFeatured] = useState(false);
  const [seoTitle, setSeoTitle] = useState("");
  const [seoDescription, setSeoDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchAdminHelpCategories()
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  async function save(andPublish: boolean) {
    setBusy(true);
    setError(null);
    try {
      const created = await createAdminHelpArticle({
        title,
        slug: slug || undefined,
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
        is_featured: featured,
        seo_title: seoTitle || null,
        seo_description: seoDescription || null,
        status: andPublish ? "published" : "draft",
      });
      toast.push({
        tone: "success",
        title: andPublish ? "Published" : "Draft saved",
      });
      router.push(`/admin/knowledge-base/${created.id}/edit`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  function toggleAudience(code: string) {
    setAudiences((prev) =>
      prev.includes(code) ? prev.filter((a) => a !== code) : [...prev, code],
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Knowledge Base"
      title="New article"
      description="Create a Help Center draft. Prefer archive over hard delete later."
      actions={
        <Link href="/admin/knowledge-base">
          <Button size="sm" variant="secondary">
            Back
          </Button>
        </Link>
      }
    >
      {error ? <Alert tone="danger">{error}</Alert> : null}
      <div className="mx-auto max-w-3xl space-y-5">
        <Input
          label="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <Input
          label="Slug (optional)"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
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
          rows={14}
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
          label="Video URL (YouTube / Vimeo / external link)"
          value={videoUrl}
          onChange={(e) => setVideoUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=…"
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
          <Button disabled={busy || !title.trim()} onClick={() => void save(false)}>
            Save draft
          </Button>
          <Button
            variant="secondary"
            disabled={busy || !title.trim()}
            onClick={() => void save(true)}
          >
            Save & publish
          </Button>
        </div>
      </div>
    </DashboardShell>
  );
}
