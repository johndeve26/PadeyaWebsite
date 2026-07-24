"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Badge, Button, Input, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  archiveAdminHelpArticle,
  fetchAdminHelpArticles,
  publishAdminHelpArticle,
  seedAdminHelp,
  type HelpArticle,
} from "@/lib/knowledge-base/api";

export default function AdminKnowledgeBaseListPage() {
  const toast = useToast();
  const [rows, setRows] = useState<HelpArticle[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setRows(await fetchAdminHelpArticles());
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

  async function act(id: string, kind: "publish" | "archive") {
    setBusy(true);
    try {
      if (kind === "publish") await publishAdminHelpArticle(id);
      else await archiveAdminHelpArticle(id);
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
      title="Knowledge Base"
      description="Help Center articles for fans, hosts, and admins on Pàdéyá."
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
                  await seedAdminHelp();
                  toast.push({ tone: "success", title: "Help content seeded" });
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
          <Link href="/admin/knowledge-base/insights">
            <Button size="sm" variant="secondary">
              Insights
            </Button>
          </Link>
          <Link href="/admin/knowledge-base/categories">
            <Button size="sm" variant="secondary">
              Categories
            </Button>
          </Link>
          <Link href="/admin/knowledge-base/new">
            <Button size="sm">New article</Button>
          </Link>
        </div>
      }
    >
      {error ? <Alert tone="danger">{error}</Alert> : null}
      <div className="mb-4 max-w-md">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter by title or slug"
        />
      </div>
      <ul className="divide-y divide-border border-t border-border">
        {filtered.map((row) => (
          <li
            key={row.id}
            className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0">
              <Link
                href={`/admin/knowledge-base/${row.id}/edit`}
                className="font-semibold text-heading hover:text-primary-text"
              >
                {row.title}
              </Link>
              <p className="mt-1 truncate text-xs text-muted-foreground">
                /help/articles/{row.slug}
                {row.category ? ` · ${row.category.name}` : null}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                tone={
                  row.status === "published"
                    ? "success"
                    : row.status === "archived"
                      ? "neutral"
                      : "warning"
                }
              >
                {row.status}
              </Badge>
              {row.status !== "published" ? (
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void act(row.id, "publish")}
                >
                  Publish
                </Button>
              ) : (
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void act(row.id, "archive")}
                >
                  Archive
                </Button>
              )}
              <Link href={`/admin/knowledge-base/${row.id}/edit`}>
                <Button size="sm" variant="ghost">
                  Edit
                </Button>
              </Link>
            </div>
          </li>
        ))}
      </ul>
      {!filtered.length && !error ? (
        <p className="py-8 text-sm text-muted-foreground">
          No articles yet. Seed demo content or create one.
        </p>
      ) : null}
    </DashboardShell>
  );
}
