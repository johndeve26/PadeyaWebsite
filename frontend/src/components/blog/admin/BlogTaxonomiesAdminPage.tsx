"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmAction,
  EmptyState,
  Input,
  Select,
  SkeletonLoader,
  Textarea,
  useToast,
} from "@/components/ui";
import { useAuth } from "@/components/auth/AuthProvider";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import {
  archiveAdminBlogCategory,
  archiveAdminBlogMediaRole,
  archiveAdminBlogPostType,
  archiveAdminBlogTag,
  createAdminBlogCategory,
  createAdminBlogMediaRole,
  createAdminBlogPostType,
  createAdminBlogTag,
  fetchAdminBlogCategories,
  fetchAdminBlogMediaRoles,
  fetchAdminBlogPostTypes,
  fetchAdminBlogTags,
  reorderAdminBlogCategories,
  reorderAdminBlogMediaRoles,
  reorderAdminBlogPostTypes,
  reorderAdminBlogTags,
  restoreAdminBlogCategory,
  restoreAdminBlogMediaRole,
  restoreAdminBlogPostType,
  restoreAdminBlogTag,
  updateAdminBlogCategory,
  updateAdminBlogMediaRole,
  updateAdminBlogPostType,
  updateAdminBlogTag,
  type BlogCategory,
  type BlogMediaRole,
  type BlogPostType,
  type BlogTag,
} from "@/lib/blog-api";
import { cn } from "@/lib/cn";

const TABS = [
  { id: "categories", label: "Categories" },
  { id: "tags", label: "Tags" },
  { id: "post-types", label: "Post types" },
  { id: "media-roles", label: "Media roles" },
] as const;

type TabId = (typeof TABS)[number]["id"];
type StatusFilter = "active" | "archived" | "all";

type TermRow = {
  id: string;
  name: string;
  slug?: string;
  key?: string;
  description?: string | null;
  is_active?: boolean;
  is_system?: boolean;
  is_required?: boolean;
  usage_count?: number;
  sort_order?: number;
  storage_folder?: string;
  seo_title?: string | null;
  seo_description?: string | null;
};

function isActive(row: TermRow) {
  return row.is_active !== false;
}

export function BlogTaxonomiesAdminPage() {
  const toast = useToast();
  const router = useRouter();
  const search = useSearchParams();
  const { user } = useAuth();
  const canManage = userHasPermission(user, "admin.blog.taxonomy.manage");

  const tabParam = (search.get("tab") || "categories") as TabId;
  const tab: TabId = TABS.some((t) => t.id === tabParam) ? tabParam : "categories";

  const [status, setStatus] = useState<StatusFilter>("active");
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<TermRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<TermRow | null>(null);
  const [creating, setCreating] = useState(false);

  const setTab = (next: TabId) => {
    router.replace(`/admin/blog/taxonomies?tab=${next}`);
    setQ("");
    setEditing(null);
    setCreating(false);
  };

  const load = useCallback(async () => {
    setError(null);
    setRows(null);
    try {
      const includeArchived = status !== "active";
      const activeOnly = status === "active";
      if (tab === "categories") {
        setRows(await fetchAdminBlogCategories({ includeArchived, activeOnly }));
      } else if (tab === "tags") {
        setRows(await fetchAdminBlogTags({ includeArchived, activeOnly }));
      } else if (tab === "post-types") {
        setRows(await fetchAdminBlogPostTypes({ includeArchived, activeOnly }));
      } else {
        setRows(await fetchAdminBlogMediaRoles({ includeArchived, activeOnly }));
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load");
      setRows([]);
    }
  }, [tab, status]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const list = rows ?? [];
    const needle = q.trim().toLowerCase();
    return list.filter((r) => {
      if (status === "active" && !isActive(r)) return false;
      if (status === "archived" && isActive(r)) return false;
      if (!needle) return true;
      return (
        r.name.toLowerCase().includes(needle) ||
        (r.slug || "").toLowerCase().includes(needle) ||
        (r.key || "").toLowerCase().includes(needle)
      );
    });
  }, [rows, q, status]);

  async function onArchive(id: string) {
    setBusy(true);
    try {
      if (tab === "categories") await archiveAdminBlogCategory(id);
      else if (tab === "tags") await archiveAdminBlogTag(id);
      else if (tab === "post-types") await archiveAdminBlogPostType(id);
      else await archiveAdminBlogMediaRole(id);
      toast.push({ tone: "success", title: "Archived" });
      await load();
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Archive failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function onRestore(id: string) {
    setBusy(true);
    try {
      if (tab === "categories") await restoreAdminBlogCategory(id);
      else if (tab === "tags") await restoreAdminBlogTag(id);
      else if (tab === "post-types") await restoreAdminBlogPostType(id);
      else await restoreAdminBlogMediaRole(id);
      toast.push({ tone: "success", title: "Restored" });
      await load();
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Restore failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function onMove(id: string, dir: -1 | 1) {
    if (!rows || !canManage) return;
    const ids = [...rows].sort(
      (a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0),
    );
    const idx = ids.findIndex((r) => r.id === id);
    const swap = idx + dir;
    if (idx < 0 || swap < 0 || swap >= ids.length) return;
    const next = [...ids];
    [next[idx], next[swap]] = [next[swap], next[idx]];
    const ordered = next.map((r) => r.id);
    setBusy(true);
    try {
      if (tab === "categories") await reorderAdminBlogCategories(ordered);
      else if (tab === "tags") await reorderAdminBlogTags(ordered);
      else if (tab === "post-types") await reorderAdminBlogPostTypes(ordered);
      else await reorderAdminBlogMediaRoles(ordered);
      await load();
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Reorder failed",
      });
    } finally {
      setBusy(false);
    }
  }

  const descriptions: Record<TabId, string> = {
    categories: "Flat topic hubs for public blog category pages.",
    tags: "Cross-cutting labels for discovery and related posts.",
    "post-types": "Editorial formats used in Blog Studio planning and metadata.",
    "media-roles": "Blog image roles (cover, OG, inline). System keys are protected.",
  };

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Blog"
      title="Taxonomies"
      description={descriptions[tab]}
      actions={
        <div className="flex flex-wrap gap-2">
          <Link
            href="/admin/blog"
            className="inline-flex h-9 items-center rounded-[var(--radius-sm)] border border-border px-3 text-sm font-semibold"
          >
            Back to posts
          </Link>
          {canManage ? (
            <Button size="sm" onClick={() => { setCreating(true); setEditing(null); }}>
              Add
            </Button>
          ) : null}
        </div>
      }
    >
      <div className="flex flex-wrap gap-2 border-b border-border pb-3">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              "rounded-[var(--radius-sm)] px-3 py-1.5 text-sm font-semibold transition-colors",
              tab === t.id
                ? "bg-primary text-primary-foreground"
                : "bg-surface-inset text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <Input
          label="Search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs"
        />
        <Select
          label="Status"
          value={status}
          onChange={(e) => setStatus(e.target.value as StatusFilter)}
          className="w-40"
        >
          <option value="active">Active</option>
          <option value="archived">Archived</option>
          <option value="all">All</option>
        </Select>
      </div>

      {error ? (
        <Alert tone="danger" title="Error" className="mt-4">
          {error}
        </Alert>
      ) : null}

      {(creating || editing) && canManage ? (
        <TermEditor
          tab={tab}
          initial={editing}
          busy={busy}
          onCancel={() => {
            setCreating(false);
            setEditing(null);
          }}
          onSaved={async () => {
            setCreating(false);
            setEditing(null);
            toast.push({ tone: "success", title: "Saved" });
            await load();
          }}
          onError={(msg) => toast.push({ tone: "danger", title: msg })}
          setBusy={setBusy}
        />
      ) : null}

      <div className="mt-6">
        {rows === null ? (
          <SkeletonLoader lines={5} />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No terms"
            description={
              canManage
                ? "Create a term or switch the status filter."
                : "Nothing matches this filter."
            }
          />
        ) : (
          <ul className="space-y-2">
            {filtered.map((row) => (
              <li key={row.id} className="list-none">
              <Card
                className="flex flex-wrap items-center justify-between gap-3"
              >
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-foreground">{row.name}</span>
                    {row.key ? (
                      <Badge tone="outline" size="sm">
                        {row.key}
                      </Badge>
                    ) : null}
                    {row.slug ? (
                      <Badge tone="outline" size="sm">
                        {row.slug}
                      </Badge>
                    ) : null}
                    {!isActive(row) ? (
                      <Badge tone="neutral" size="sm">
                        Archived
                      </Badge>
                    ) : null}
                    {row.is_system ? (
                      <Badge tone="outline" size="sm">
                        System
                      </Badge>
                    ) : null}
                    {row.is_required ? (
                      <Badge tone="outline" size="sm">
                        Required
                      </Badge>
                    ) : null}
                    <Badge tone="outline" size="sm">
                      {row.usage_count ?? 0} uses
                    </Badge>
                  </div>
                  {row.description ? (
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {row.description}
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2">
                  {canManage ? (
                    <>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busy}
                        onClick={() => void onMove(row.id, -1)}
                      >
                        Up
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busy}
                        onClick={() => void onMove(row.id, 1)}
                      >
                        Down
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          setEditing(row);
                          setCreating(false);
                        }}
                      >
                        Edit
                      </Button>
                      {isActive(row) ? (
                        <ConfirmAction
                          label="Archive"
                          title={`Archive ${row.name}?`}
                          description={
                            row.is_required
                              ? "Required system roles cannot be archived."
                              : "Existing posts keep this term; new posts cannot select it."
                          }
                          confirmLabel="Archive"
                          variant="ghost"
                          onConfirm={() => onArchive(row.id)}
                        />
                      ) : (
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={busy}
                          onClick={() => void onRestore(row.id)}
                        >
                          Restore
                        </Button>
                      )}
                    </>
                  ) : null}
                  {tab === "categories" && row.slug ? (
                    <Link
                      href={`/blog/category/${row.slug}`}
                      className="inline-flex h-8 items-center text-sm font-semibold text-foreground underline decoration-primary underline-offset-2"
                    >
                      View
                    </Link>
                  ) : null}
                  {tab === "tags" && row.slug ? (
                    <Link
                      href={`/blog/tag/${row.slug}`}
                      className="inline-flex h-8 items-center text-sm font-semibold text-foreground underline decoration-primary underline-offset-2"
                    >
                      View
                    </Link>
                  ) : null}
                </div>
              </Card>
              </li>
            ))}
          </ul>
        )}
      </div>
    </DashboardShell>
  );
}

function TermEditor({
  tab,
  initial,
  busy,
  onCancel,
  onSaved,
  onError,
  setBusy,
}: {
  tab: TabId;
  initial: TermRow | null;
  busy: boolean;
  onCancel: () => void;
  onSaved: () => Promise<void>;
  onError: (msg: string) => void;
  setBusy: (v: boolean) => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [slug, setSlug] = useState(initial?.slug ?? "");
  const [key, setKey] = useState(initial?.key ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [seoTitle, setSeoTitle] = useState(initial?.seo_title ?? "");
  const [seoDescription, setSeoDescription] = useState(
    initial?.seo_description ?? "",
  );
  const [confirmSlug, setConfirmSlug] = useState(false);
  const [folder, setFolder] = useState(initial?.storage_folder ?? "content");

  async function save() {
    setBusy(true);
    try {
      if (tab === "categories") {
        if (initial) {
          await updateAdminBlogCategory(initial.id, {
            name,
            slug: slug || undefined,
            description: description || null,
            seo_title: seoTitle || null,
            seo_description: seoDescription || null,
            confirm_slug_change: confirmSlug,
          });
        } else {
          await createAdminBlogCategory({
            name,
            slug: slug || undefined,
            description: description || undefined,
            seo_title: seoTitle || undefined,
            seo_description: seoDescription || undefined,
          });
        }
      } else if (tab === "tags") {
        if (initial) {
          await updateAdminBlogTag(initial.id, {
            name,
            slug: slug || undefined,
            description: description || null,
            confirm_slug_change: confirmSlug,
          });
        } else {
          await createAdminBlogTag({
            name,
            slug: slug || undefined,
            description: description || undefined,
          });
        }
      } else if (tab === "post-types") {
        if (initial) {
          await updateAdminBlogPostType(initial.id, {
            name,
            slug: initial.is_system ? undefined : slug || undefined,
            description: description || null,
          });
        } else {
          await createAdminBlogPostType({
            name,
            key: key || undefined,
            slug: slug || undefined,
            description: description || undefined,
          });
        }
      } else if (initial) {
        await updateAdminBlogMediaRole(initial.id, {
          name,
          description: description || null,
        });
      } else {
        await createAdminBlogMediaRole({
          name,
          key,
          description: description || undefined,
          storage_folder: folder,
        });
      }
      await onSaved();
    } catch (e) {
      onError(e instanceof ApiError ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="mt-4 space-y-3">
      <h3 className="text-sm font-semibold">
        {initial ? `Edit ${initial.name}` : "Create term"}
      </h3>
      <div className="grid gap-3 sm:grid-cols-2">
        <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} />
        {tab !== "media-roles" || !initial ? (
          <Input
            label={tab === "media-roles" || tab === "post-types" ? "Key" : "Slug"}
            value={tab === "media-roles" || (tab === "post-types" && !initial) ? key : slug}
            onChange={(e) => {
              if (tab === "media-roles" || (tab === "post-types" && !initial)) {
                setKey(e.target.value);
              } else {
                setSlug(e.target.value);
              }
            }}
            disabled={Boolean(initial && (initial.is_system || tab === "media-roles"))}
            hint={
              initial?.is_system
                ? "System key is immutable"
                : tab === "categories" || tab === "tags"
                  ? "Public URL segment"
                  : undefined
            }
          />
        ) : (
          <Input label="Key" value={key} disabled hint="System key is immutable" />
        )}
      </div>
      {(tab === "categories" || tab === "tags" || tab === "post-types") && initial ? (
        <Input
          label="Slug"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          disabled={tab === "post-types" && Boolean(initial.is_system)}
        />
      ) : null}
      {(tab === "categories" || tab === "tags") &&
      initial &&
      slug &&
      slug !== initial.slug ? (
        <label className="flex items-start gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={confirmSlug}
            onChange={(e) => setConfirmSlug(e.target.checked)}
            className="mt-1"
          />
          Confirm slug change (creates a public redirect from the old URL)
        </label>
      ) : null}
      {!initial && tab === "media-roles" ? (
        <Select
          label="Storage folder"
          value={folder}
          onChange={(e) => setFolder(e.target.value)}
        >
          <option value="content">content</option>
          <option value="covers">covers</option>
        </Select>
      ) : null}
      <Textarea
        label="Description"
        rows={2}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      {tab === "categories" ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <Input
            label="SEO title"
            value={seoTitle}
            onChange={(e) => setSeoTitle(e.target.value)}
          />
          <Input
            label="SEO description"
            value={seoDescription}
            onChange={(e) => setSeoDescription(e.target.value)}
          />
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button disabled={busy || !name.trim()} onClick={() => void save()}>
          Save
        </Button>
        <Button variant="secondary" disabled={busy} onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </Card>
  );
}

// silence unused type imports used for clarity in editors
void (null as unknown as BlogCategory | BlogTag | BlogPostType | BlogMediaRole);
