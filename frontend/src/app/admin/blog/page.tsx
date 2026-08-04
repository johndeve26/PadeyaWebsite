"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  ConfirmAction,
  DataTable,
  FilterBar,
  Input,
  Select,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  deleteAdminBlogPost,
  fetchAdminBlogPosts,
  publishAdminBlogPost,
  seedAdminBlog,
  unpublishAdminBlogPost,
  type BlogPost,
} from "@/lib/blog-api";
import { formatDate } from "@/lib/format";

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "published", label: "Published" },
  { value: "draft", label: "Draft" },
  { value: "archived", label: "Archived" },
];

const SORT_OPTIONS = [
  { value: "updated_desc", label: "Updated (newest)" },
  { value: "updated_asc", label: "Updated (oldest)" },
  { value: "title_asc", label: "Title (A–Z)" },
  { value: "title_desc", label: "Title (Z–A)" },
  { value: "published_desc", label: "Published (newest)" },
  { value: "published_asc", label: "Published (oldest)" },
  { value: "status_asc", label: "Status (A–Z)" },
  { value: "status_desc", label: "Status (Z–A)" },
] as const;

type SortKey = (typeof SORT_OPTIONS)[number]["value"];

function comparePosts(a: BlogPost, b: BlogPost, sortBy: SortKey): number {
  switch (sortBy) {
    case "title_asc":
      return a.title.localeCompare(b.title, undefined, { sensitivity: "base" });
    case "title_desc":
      return b.title.localeCompare(a.title, undefined, { sensitivity: "base" });
    case "updated_asc":
      return (
        new Date(a.updated_at ?? 0).getTime() -
        new Date(b.updated_at ?? 0).getTime()
      );
    case "updated_desc":
      return (
        new Date(b.updated_at ?? 0).getTime() -
        new Date(a.updated_at ?? 0).getTime()
      );
    case "published_asc":
      return (
        new Date(a.published_at ?? 0).getTime() -
        new Date(b.published_at ?? 0).getTime()
      );
    case "published_desc":
      return (
        new Date(b.published_at ?? 0).getTime() -
        new Date(a.published_at ?? 0).getTime()
      );
    case "status_asc":
      return a.status.localeCompare(b.status);
    case "status_desc":
      return b.status.localeCompare(a.status);
    default:
      return 0;
  }
}

export default function AdminBlogListPage() {
  const toast = useToast();
  const [rows, setRows] = useState<BlogPost[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState<SortKey>("updated_desc");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [seedBusy, setSeedBusy] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    try {
      setRows(await fetchAdminBlogPosts(true));
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load");
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate list
    void load();
  }, [load]);

  useEffect(() => {
    setSelectedIds(new Set());
  }, [q, statusFilter, sortBy]);

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    return rows
      .filter((r) => {
        if (statusFilter !== "all" && r.status !== statusFilter) return false;
        if (!query) return true;
        return (
          r.title.toLowerCase().includes(query) ||
          r.slug.toLowerCase().includes(query)
        );
      })
      .sort((a, b) => comparePosts(a, b, sortBy));
  }, [rows, q, statusFilter, sortBy]);

  const selectableIds = useMemo(() => filtered.map((p) => p.id), [filtered]);

  const allSelectableChecked =
    selectableIds.length > 0 &&
    selectableIds.every((id) => selectedIds.has(id));
  const someSelectableChecked =
    selectableIds.some((id) => selectedIds.has(id)) && !allSelectableChecked;

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    setSelectedIds((prev) => {
      if (allSelectableChecked) {
        const next = new Set(prev);
        for (const id of selectableIds) next.delete(id);
        return next;
      }
      const next = new Set(prev);
      for (const id of selectableIds) next.add(id);
      return next;
    });
  }

  async function runBulkArchive(targets: string[]) {
    if (targets.length === 0) return;
    setBulkBusy(true);
    let ok = 0;
    let fail = 0;
    let lastError: string | null = null;
    try {
      for (const id of targets) {
        try {
          await deleteAdminBlogPost(id);
          ok += 1;
        } catch (err) {
          fail += 1;
          lastError = err instanceof ApiError ? err.message : "Try again";
        }
      }
      setSelectedIds(new Set());
      await load();
      if (fail === 0) {
        toast.push({
          tone: "success",
          title: `${ok} post${ok === 1 ? "" : "s"} archived`,
        });
      } else if (ok === 0) {
        toast.push({
          tone: "danger",
          title: "Bulk archive failed",
          description: lastError ?? "Try again",
        });
      } else {
        toast.push({
          tone: "danger",
          title: `${ok} archived, ${fail} failed`,
          description: lastError ?? "Review remaining posts and retry",
        });
      }
    } finally {
      setBulkBusy(false);
    }
  }

  async function act(id: string, kind: "publish" | "unpublish" | "delete") {
    setBusyId(id);
    try {
      if (kind === "publish") await publishAdminBlogPost(id);
      else if (kind === "unpublish") await unpublishAdminBlogPost(id);
      else await deleteAdminBlogPost(id);
      toast.push({ tone: "success", title: "Updated" });
      setSelectedIds((prev) => {
        if (!prev.has(id)) return prev;
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      await load();
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Action failed",
      });
    } finally {
      setBusyId(null);
    }
  }

  const busy = busyId !== null || bulkBusy || seedBusy;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Content"
      title="Blog"
      description="Create and publish editorial posts for Pàdéyá."
      actions={
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() =>
              void (async () => {
                setSeedBusy(true);
                try {
                  await seedAdminBlog();
                  toast.push({ tone: "success", title: "Demo posts seeded" });
                  await load();
                } catch (e) {
                  toast.push({
                    tone: "danger",
                    title: e instanceof ApiError ? e.message : "Seed failed",
                  });
                } finally {
                  setSeedBusy(false);
                }
              })()
            }
          >
            Seed demo
          </Button>
          <Link
            href="/admin/blog/comments"
            className="inline-flex h-9 items-center rounded-[var(--radius-sm)] border border-border px-3 text-sm font-semibold"
          >
            Comments
          </Link>
          <Link
            href="/admin/blog/taxonomies"
            className="inline-flex h-9 items-center rounded-[var(--radius-sm)] border border-border px-3 text-sm font-semibold"
          >
            Taxonomies
          </Link>
          <Link
            href="/admin/blog/new"
            className="inline-flex h-9 items-center rounded-[var(--radius-sm)] bg-primary px-3 text-sm font-semibold text-primary-foreground"
          >
            New post
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}

      <FilterBar
        trailing={
          <span className="text-sm text-muted-foreground">
            {filtered.length} of {rows.length} posts
          </span>
        }
      >
        <Input
          label="Search"
          placeholder="Title or slug…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <Select
          label="Status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Select
          label="Sort by"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as SortKey)}
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
      </FilterBar>

      {filtered.length > 0 ? (
        <div className="mb-4 flex flex-col gap-3 rounded-[var(--radius-lg)] border border-border bg-card px-4 py-3 sm:flex-row sm:items-center sm:justify-between dark:bg-surface-elevated">
          <div className="flex flex-wrap items-center gap-4">
            <label className="inline-flex cursor-pointer items-center gap-2.5 text-sm text-foreground">
              <input
                id="admin-blog-select-all"
                type="checkbox"
                checked={allSelectableChecked}
                ref={(el) => {
                  if (el) el.indeterminate = someSelectableChecked;
                }}
                onChange={() => toggleSelectAll()}
                disabled={selectableIds.length === 0 || bulkBusy}
                className="h-4 w-4 accent-[color:var(--brand-green)] disabled:cursor-not-allowed disabled:opacity-40"
              />
              <span>Select all</span>
            </label>
            <span className="text-sm text-muted-foreground">
              {selectedIds.size > 0
                ? `${selectedIds.size} selected`
                : "Select posts to archive in bulk"}
            </span>
          </div>
          <ConfirmAction
            label="Archive selected"
            title={`Archive ${selectedIds.size} post${selectedIds.size === 1 ? "" : "s"}?`}
            description="Archived posts leave the active list but remain for history. This is soft end-of-life, not a hard delete."
            confirmLabel="Archive selected"
            tone="danger"
            size="sm"
            disabled={selectedIds.size === 0}
            busy={bulkBusy}
            onConfirm={() => runBulkArchive([...selectedIds])}
          />
        </div>
      ) : null}

      <DataTable
        rows={filtered}
        rowKey={(p) => p.id}
        emptyTitle="No posts"
        emptyDescription={
          q.trim() || statusFilter !== "all"
            ? "Try a different search or filter."
            : "Create one or seed demo content."
        }
        columns={[
          {
            key: "select",
            header: "",
            className: "w-10",
            cell: (p) => (
              <input
                type="checkbox"
                checked={selectedIds.has(p.id)}
                disabled={bulkBusy}
                onChange={() => toggleSelect(p.id)}
                aria-label={`Select ${p.title}`}
                className="h-4 w-4 accent-[color:var(--brand-green)] disabled:cursor-not-allowed disabled:opacity-40"
              />
            ),
          },
          {
            key: "title",
            header: "Post",
            primary: true,
            cell: (p) => (
              <div className="space-y-0.5">
                <Link
                  href={`/admin/blog/${p.id}/edit`}
                  className="font-semibold text-heading hover:text-primary"
                >
                  {p.title}
                </Link>
                <p className="text-xs text-muted-foreground">/{p.slug}</p>
              </div>
            ),
          },
          {
            key: "status",
            header: "Status",
            cell: (p) => (
              <Badge tone={p.status === "published" ? "success" : "neutral"}>
                {p.status}
              </Badge>
            ),
          },
          {
            key: "updated",
            header: "Updated",
            cell: (p) => (
              <span className="text-muted-foreground">
                {p.updated_at ? formatDate(p.updated_at) : "—"}
              </span>
            ),
          },
          {
            key: "actions",
            header: "",
            className: "text-right",
            cell: (p) => (
              <div className="flex flex-wrap items-center justify-end gap-2">
                {p.status !== "published" ? (
                  <Button
                    size="sm"
                    disabled={busy}
                    onClick={() => void act(p.id, "publish")}
                  >
                    Publish
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void act(p.id, "unpublish")}
                  >
                    Unpublish
                  </Button>
                )}
                <ConfirmAction
                  label="Archive"
                  title="Archive this post?"
                  description="Archived posts are hidden from the active list but kept for history."
                  confirmLabel="Archive"
                  tone="danger"
                  size="sm"
                  disabled={busy}
                  busy={busyId === p.id}
                  onConfirm={() => act(p.id, "delete")}
                />
              </div>
            ),
          },
        ]}
      />
    </DashboardShell>
  );
}
