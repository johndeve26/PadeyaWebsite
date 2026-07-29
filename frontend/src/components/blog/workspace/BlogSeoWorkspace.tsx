"use client";
// BlogSeoWorkspace — SEO & Social tab: form fields + live previews

import { useEffect, useState } from "react";

import { useBlogStudio } from "@/components/blog/studio/BlogStudioProvider";
import { ImageUrlOrUploadField } from "@/components/media/ImageUrlOrUploadField";
import { Input, Select, Textarea, Badge } from "@/components/ui";
import {
  fetchAdminBlogCategories,
  fetchAdminBlogMediaRoles,
  fetchAdminBlogPostTypes,
  fetchAdminBlogTags,
  type BlogCategory,
  type BlogMediaRole,
  type BlogPostType,
  type BlogTag,
} from "@/lib/blog-api";
import { seoTitleScore, seoDescriptionScore } from "@/lib/blog-workspace";

function CharCount({ value, min, max }: { value: string; min: number; max: number }) {
  const len = value.length;
  const ok = len >= min && len <= max;
  const warn = len > 0 && !ok;
  return (
    <span className={`text-xs ${warn ? "text-amber-600" : "text-muted-foreground"}`}>
      {len} / {min}–{max}
    </span>
  );
}

function GooglePreview({ title, description, slug }: { title: string; description: string; slug: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4 space-y-1">
      <p className="text-xs text-muted-foreground uppercase tracking-wide font-semibold mb-2">Google preview</p>
      <div className="text-xs text-muted-foreground truncate">padeya.com / blog / {slug || "your-slug"}</div>
      <div className="text-blue-700 text-base font-medium leading-snug truncate">
        {title || "Your meta title"}
      </div>
      <div className="text-sm text-gray-600 leading-snug line-clamp-2">
        {description || "Your meta description will appear here."}
      </div>
    </div>
  );
}

function SocialPreview({ title, description, imageUrl }: { title: string; description: string; imageUrl: string }) {
  return (
    <div className="rounded-lg border border-border overflow-hidden bg-surface">
      <p className="text-xs text-muted-foreground uppercase tracking-wide font-semibold p-3">Social card preview</p>
      {imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={imageUrl} alt="OG preview" className="w-full h-40 object-cover" />
      ) : (
        <div className="w-full h-40 bg-surface-muted flex items-center justify-center text-muted-foreground text-sm">
          No image set
        </div>
      )}
      <div className="p-3 space-y-1">
        <div className="text-xs text-muted-foreground">padeya.com</div>
        <div className="font-semibold text-sm truncate">{title || "Your OG title"}</div>
        <div className="text-xs text-muted-foreground line-clamp-2">{description || "Your OG description"}</div>
      </div>
    </div>
  );
}

export function BlogSeoWorkspace() {
  const studio = useBlogStudio();
  const [categories, setCategories] = useState<BlogCategory[]>([]);
  const [tags, setTags] = useState<BlogTag[]>([]);
  const [postTypes, setPostTypes] = useState<BlogPostType[]>([]);
  const [mediaRoles, setMediaRoles] = useState<BlogMediaRole[]>([]);

  useEffect(() => {
    void (async () => {
      try {
        const [c, t, p, m] = await Promise.all([
          fetchAdminBlogCategories({ includeArchived: true }),
          fetchAdminBlogTags({ includeArchived: true }),
          fetchAdminBlogPostTypes({ includeArchived: true }),
          fetchAdminBlogMediaRoles({ activeOnly: true }),
        ]);
        setCategories(c);
        setTags(t);
        setPostTypes(p);
        setMediaRoles(m);
      } catch {
        /* catalogs optional */
      }
    })();
  }, []);

  const metaTitleScore = seoTitleScore(studio.seoTitle);
  const metaDescScore = seoDescriptionScore(studio.seoDescription);
  const coverRole = mediaRoles.find((r) => r.key === "cover");
  const ogRole = mediaRoles.find((r) => r.key === "og");

  const activeCategories = categories.filter((c) => c.is_active !== false);
  const selectedCategory = categories.find((c) => c.id === studio.categoryId);
  const categoryOptions =
    selectedCategory && selectedCategory.is_active === false
      ? [selectedCategory, ...activeCategories.filter((c) => c.id !== selectedCategory.id)]
      : activeCategories;

  const activeTypes = postTypes.filter((t) => t.is_active !== false);
  const selectedType = postTypes.find((t) => t.id === studio.postTypeId);
  const typeOptions =
    selectedType && selectedType.is_active === false
      ? [selectedType, ...activeTypes.filter((t) => t.id !== selectedType.id)]
      : activeTypes;

  const activeTags = tags.filter((t) => t.is_active !== false);
  const selectedTags = tags.filter((t) => studio.tagIds.includes(t.id));

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-6">
          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Metadata
            </h2>
            <Select
              label="Category"
              value={studio.categoryId || ""}
              onChange={(e) => studio.patch({ categoryId: e.target.value, dirty: true })}
            >
              <option value="">No category</option>
              {categoryOptions.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                  {c.is_active === false ? " (Archived)" : ""}
                </option>
              ))}
            </Select>
            <Select
              label="Post type"
              value={studio.postTypeId || ""}
              onChange={(e) => {
                const id = e.target.value;
                const row = postTypes.find((t) => t.id === id);
                studio.patch({ postTypeId: id, dirty: true });
                if (row) {
                  studio.setBrief({
                    ...studio.brief,
                    post_type_id: id,
                    post_type_key: row.key,
                    post_type_name: row.name,
                    content_type: row.name,
                  });
                } else {
                  studio.setBrief({
                    ...studio.brief,
                    post_type_id: undefined,
                    post_type_key: undefined,
                    post_type_name: undefined,
                  });
                }
              }}
            >
              <option value="">No post type</option>
              {typeOptions.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                  {t.is_active === false ? " (Archived)" : ""}
                </option>
              ))}
            </Select>
            <div>
              <p className="mb-2 text-sm font-semibold text-foreground">Tags</p>
              <div className="flex flex-wrap gap-2">
                {selectedTags.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    className="inline-flex items-center gap-1"
                    onClick={() =>
                      studio.patch({
                        tagIds: studio.tagIds.filter((id) => id !== t.id),
                        dirty: true,
                      })
                    }
                  >
                    <Badge tone="accent" size="sm">
                      {t.name}
                      {t.is_active === false ? " · Archived" : ""}
                      {" ×"}
                    </Badge>
                  </button>
                ))}
                {activeTags
                  .filter((t) => !studio.tagIds.includes(t.id))
                  .map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() =>
                        studio.patch({
                          tagIds: [...studio.tagIds, t.id],
                          dirty: true,
                        })
                      }
                    >
                      <Badge tone="outline" size="sm">
                        + {t.name}
                      </Badge>
                    </button>
                  ))}
              </div>
            </div>
            <ImageUrlOrUploadField
              label={coverRole?.name || "Featured image"}
              hint="Uses the cover media role"
              value={studio.coverUrl}
              onChange={(url) => studio.patch({ coverUrl: url, dirty: true })}
              blogMediaRole="cover"
              previewClassName="h-24 w-40"
            />
            <ImageUrlOrUploadField
              label={ogRole?.name || "Open Graph image"}
              hint="Uses the og media role"
              value={studio.ogImageUrl}
              onChange={(url) => studio.patch({ ogImageUrl: url, dirty: true })}
              blogMediaRole="og"
              previewClassName="h-24 w-40"
            />
          </section>

          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Search</h2>
            <Input
              label="Slug"
              value={studio.slug}
              onChange={(e) => studio.patch({ slug: e.target.value, dirty: true })}
              placeholder="your-post-slug"
            />
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Meta title</label>
                <CharCount value={studio.seoTitle} min={50} max={60} />
              </div>
              <input
                className="w-full rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                value={studio.seoTitle}
                onChange={(e) => studio.patch({ seoTitle: e.target.value, dirty: true })}
                placeholder="Meta title (50-60 chars)"
              />
              {!metaTitleScore.ok && studio.seoTitle ? (
                <p className="text-xs text-amber-600">{metaTitleScore.message}</p>
              ) : null}
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Meta description</label>
                <CharCount value={studio.seoDescription} min={120} max={160} />
              </div>
              <textarea
                rows={3}
                className="w-full rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                value={studio.seoDescription}
                onChange={(e) => studio.patch({ seoDescription: e.target.value, dirty: true })}
                placeholder="Meta description (120-160 chars)"
              />
              {!metaDescScore.ok && studio.seoDescription ? (
                <p className="text-xs text-amber-600">{metaDescScore.message}</p>
              ) : null}
              {studio.excerpt ? (
                <button
                  type="button"
                  className="text-xs text-primary hover:underline"
                  onClick={() => studio.patch({ seoDescription: studio.excerpt, dirty: true })}
                >
                  Use article summary
                </button>
              ) : null}
            </div>
            <Input
              label="Canonical URL"
              value={studio.canonicalUrl}
              onChange={(e) => studio.patch({ canonicalUrl: e.target.value, dirty: true })}
              placeholder="https://…"
            />
            <Input
              label="Primary / focus keyword"
              value={studio.focusKeyword}
              onChange={(e) => studio.patch({ focusKeyword: e.target.value, dirty: true })}
            />
            <Textarea
              label="Secondary keywords"
              rows={2}
              value={studio.secondaryKeywords.join(", ")}
              onChange={(e) =>
                studio.patch({
                  secondaryKeywords: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                  dirty: true,
                })
              }
            />
          </section>

          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Social</h2>
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">OG title</label>
              </div>
              <input
                className="w-full rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                value={studio.ogTitle}
                onChange={(e) => studio.patch({ ogTitle: e.target.value, dirty: true })}
                placeholder="Open Graph title"
              />
              {studio.title ? (
                <button
                  type="button"
                  className="text-xs text-primary hover:underline"
                  onClick={() => studio.patch({ ogTitle: studio.title, dirty: true })}
                >
                  Use article title
                </button>
              ) : null}
            </div>
            <Textarea
              label="OG description"
              rows={2}
              value={studio.excerpt}
              onChange={(e) => studio.patch({ excerpt: e.target.value, dirty: true })}
              placeholder="Open Graph description"
            />
            <Textarea
              label="Social share text"
              rows={2}
              value={studio.socialShareText}
              onChange={(e) => studio.patch({ socialShareText: e.target.value, dirty: true })}
            />
          </section>
        </div>

        <div className="space-y-6">
          <GooglePreview
            title={studio.seoTitle || studio.title}
            description={studio.seoDescription || studio.excerpt}
            slug={studio.slug}
          />
          <SocialPreview
            title={studio.ogTitle || studio.title}
            description={studio.excerpt}
            imageUrl={studio.ogImageUrl || studio.coverUrl}
          />
        </div>
      </div>
    </div>
  );
}
