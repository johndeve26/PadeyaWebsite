"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Input,
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

export default function AdminBlogListPage() {
  const toast = useToast();
  const [rows, setRows] = useState<BlogPost[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);

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

  const filtered = rows.filter(
    (r) =>
      !q.trim() ||
      r.title.toLowerCase().includes(q.toLowerCase()) ||
      r.slug.toLowerCase().includes(q.toLowerCase()),
  );

  async function act(id: string, kind: "publish" | "unpublish" | "delete") {
    setBusy(true);
    try {
      if (kind === "publish") await publishAdminBlogPost(id);
      else if (kind === "unpublish") await unpublishAdminBlogPost(id);
      else await deleteAdminBlogPost(id);
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
                setBusy(true);
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
                  setBusy(false);
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
            href="/admin/blog/categories"
            className="inline-flex h-9 items-center rounded-[var(--radius-sm)] border border-border px-3 text-sm font-semibold"
          >
            Categories
          </Link>
          <Link
            href="/admin/blog/tags"
            className="inline-flex h-9 items-center rounded-[var(--radius-sm)] border border-border px-3 text-sm font-semibold"
          >
            Tags
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
      <Input
        label="Search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        className="max-w-md"
      />
      <ul className="mt-6 divide-y divide-border rounded-[var(--radius-md)] border border-border">
        {filtered.map((p) => (
          <li
            key={p.id}
            className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
          >
            <div>
              <Link
                href={`/admin/blog/${p.id}/edit`}
                className="font-semibold text-heading hover:text-primary"
              >
                {p.title}
              </Link>
              <p className="text-xs text-muted-foreground">/{p.slug}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={p.status === "published" ? "success" : "neutral"}>
                {p.status}
              </Badge>
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
              <Button
                size="sm"
                variant="danger"
                disabled={busy}
                onClick={() => void act(p.id, "delete")}
              >
                Archive
              </Button>
            </div>
          </li>
        ))}
        {!filtered.length ? (
          <li className="px-4 py-8 text-sm text-muted-foreground">
            No posts. Create one or seed demo content.
          </li>
        ) : null}
      </ul>
    </DashboardShell>
  );
}
